import { checkApiKey, getServerProfile } from "@/lib/server/server-chat-helpers"
import { ChatSettings } from "@/types"
import { OpenAIStream, StreamingTextResponse } from "ai"
import { ServerRuntime } from "next"
import OpenAI from "openai"
import { ChatCompletionCreateParamsBase } from "openai/resources/chat/completions.mjs"
import { getMCPTools, executeMCPTool } from "@/lib/mcp/mcp-integration"

export const runtime: ServerRuntime = "nodejs"

export async function POST(request: Request) {
  const json = await request.json()
  const { chatSettings, messages } = json as {
    chatSettings: ChatSettings
    messages: any[]
  }

  try {
    const profile = await getServerProfile()

    checkApiKey(profile.openrouter_api_key, "OpenRouter")

    const openai = new OpenAI({
      apiKey: profile.openrouter_api_key || "",
      baseURL: "https://openrouter.ai/api/v1"
    })

    // Get MCP tools
    const mcpTools = await getMCPTools()
    console.log('MCP Tools found for OpenRouter:', mcpTools.length, mcpTools.map(t => t.function?.name))

    // Convert MCP tools to OpenAI format
    const openaiTools = mcpTools.map(tool => ({
      type: 'function' as const,
      function: {
        name: tool.function.name,
        description: tool.function.description,
        parameters: tool.function.parameters
      }
    }))

    // First, make a non-streaming request to check for tool calls
    const firstResponse = await openai.chat.completions.create({
      model: chatSettings.model as ChatCompletionCreateParamsBase["model"],
      messages: messages as ChatCompletionCreateParamsBase["messages"],
      temperature: chatSettings.temperature,
      max_tokens: undefined,
      tools: openaiTools.length > 0 ? openaiTools : undefined,
      stream: false
    })

    const message = firstResponse.choices[0].message
    messages.push(message)
    const toolCalls = message.tool_calls || []

    // Handle tool calls if any
    if (toolCalls.length > 0) {
      for (const toolCall of toolCalls) {
        const functionCall = toolCall.function
        const functionName = functionCall.name
        const argumentsString = toolCall.function.arguments.trim()
        const parsedArgs = JSON.parse(argumentsString)

        // Check if this is an MCP tool
        if (functionName.startsWith('firecrawl_') || 
            functionName.startsWith('columbia-lake-agents_') || 
            functionName.startsWith('excel-mcp_')) {
          try {
            const mcpResult = await executeMCPTool(functionName, parsedArgs)
            console.log('MCP tool result:', mcpResult)
            
            messages.push({
              tool_call_id: toolCall.id,
              role: "tool",
              name: functionName,
              content: JSON.stringify(mcpResult)
            })
          } catch (error) {
            console.error('MCP tool execution failed:', error)
            
            messages.push({
              tool_call_id: toolCall.id,
              role: "tool", 
              name: functionName,
              content: JSON.stringify({ error: error.message })
            })
          }
        }
      }

      // Make final streaming request with tool results
      const finalResponse = await openai.chat.completions.create({
        model: chatSettings.model as ChatCompletionCreateParamsBase["model"],
        messages: messages as ChatCompletionCreateParamsBase["messages"],
        temperature: chatSettings.temperature,
        max_tokens: undefined,
        stream: true
      })

      const stream = OpenAIStream(finalResponse)
      return new StreamingTextResponse(stream)
    }

    // No tool calls, just stream the response
    const response = await openai.chat.completions.create({
      model: chatSettings.model as ChatCompletionCreateParamsBase["model"],
      messages: messages as ChatCompletionCreateParamsBase["messages"],
      temperature: chatSettings.temperature,
      max_tokens: undefined,
      stream: true
    })

    const stream = OpenAIStream(response)
    return new StreamingTextResponse(stream)
  } catch (error: any) {
    let errorMessage = error.message || "An unexpected error occurred"
    const errorCode = error.status || 500

    if (errorMessage.toLowerCase().includes("api key not found")) {
      errorMessage =
        "OpenRouter API Key not found. Please set it in your profile settings."
    }

    return new Response(JSON.stringify({ message: errorMessage }), {
      status: errorCode
    })
  }
}
