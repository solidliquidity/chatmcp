import { CHAT_SETTING_LIMITS } from "@/lib/chat-setting-limits"
import { checkApiKey, getServerProfile } from "@/lib/server/server-chat-helpers"
import { getBase64FromDataURL, getMediaTypeFromDataURL } from "@/lib/utils"
import { ChatSettings } from "@/types"
import Anthropic from "@anthropic-ai/sdk"
import { AnthropicStream, StreamingTextResponse } from "ai"
import { NextRequest, NextResponse } from "next/server"
import { getMCPTools, generateSystemPrompt } from "@/lib/mcp/mcp-integration"
import { executeMCPTool } from "@/lib/mcp/multi-mcp-client"

export const runtime = "edge"

export async function POST(request: NextRequest) {
  const json = await request.json()
  const { chatSettings, messages } = json as {
    chatSettings: ChatSettings
    messages: any[]
  }

  try {
    const profile = await getServerProfile()

    checkApiKey(profile.anthropic_api_key, "Anthropic")

    // Get MCP tools
    const mcpTools = await getMCPTools()
    console.log('🔧 MCP Tools Debug (Anthropic):', {
      mcpToolsCount: mcpTools.length,
      mcpToolNames: mcpTools.map(t => t.function?.name || 'unknown').slice(0, 10),
      excelToolsCount: mcpTools.filter(t => (t.function?.name || '').includes('excel')).length
    })

    // Generate system prompt for MCP tools
    const systemPrompt = generateSystemPrompt(mcpTools);
    console.log('📝 System Prompt Debug (Anthropic):', {
      systemPromptLength: systemPrompt.length,
      hasExcelInPrompt: systemPrompt.includes('excel'),
      hasSystemPrompt: systemPrompt.length > 0
    })

    let ANTHROPIC_FORMATTED_MESSAGES: any = messages.slice(1)

    ANTHROPIC_FORMATTED_MESSAGES = ANTHROPIC_FORMATTED_MESSAGES?.map(
      (message: any) => {
        const messageContent =
          typeof message?.content === "string"
            ? [message.content]
            : message?.content

        return {
          ...message,
          content: messageContent.map((content: any) => {
            if (typeof content === "string") {
              // Handle the case where content is a string
              return { type: "text", text: content }
            } else if (
              content?.type === "image_url" &&
              content?.image_url?.url?.length
            ) {
              return {
                type: "image",
                source: {
                  type: "base64",
                  media_type: getMediaTypeFromDataURL(content.image_url.url),
                  data: getBase64FromDataURL(content.image_url.url)
                }
              }
            } else {
              return content
            }
          })
        }
      }
    )

    const anthropic = new Anthropic({
      apiKey: profile.anthropic_api_key || ""
    })

    try {
      console.log('🚀 Anthropic API Request Debug:', {
        model: chatSettings.model,
        hasSystemPrompt: true,
        toolsCount: mcpTools.length,
        toolsIncluded: mcpTools.length > 0 ? 'YES' : 'NO'
      })

      const response = await anthropic.messages.create({
        model: chatSettings.model,
        messages: ANTHROPIC_FORMATTED_MESSAGES,
        temperature: chatSettings.temperature,
        system: systemPrompt || messages[0].content,
        max_tokens:
          CHAT_SETTING_LIMITS[chatSettings.model].MAX_TOKEN_OUTPUT_LENGTH,
        tools: mcpTools.length > 0 ? mcpTools : undefined,
        stream: true
      })

      try {
        // Handle tool calls if present
        const stream = AnthropicStream(response, {
          onToolCall: async (toolCall: any, createToolCallResult: any) => {
            console.log(`[DEBUG] Executing tool ${toolCall.toolName} with args:`, JSON.stringify(toolCall.args))
            
            try {
              const result = await executeMCPTool(toolCall.toolName, toolCall.args)
              console.log(`[DEBUG] Tool ${toolCall.toolName} result:`, result)
              return createToolCallResult({ result })
            } catch (error) {
              console.error(`Error executing MCP tool ${toolCall.toolName}:`, error)
              return createToolCallResult({ 
                error: `Error executing tool: ${error instanceof Error ? error.message : 'Unknown error'}` 
              })
            }
          }
        })
        return new StreamingTextResponse(stream)
      } catch (error: any) {
        console.error("Error parsing Anthropic API response:", error)
        return new NextResponse(
          JSON.stringify({
            message:
              "An error occurred while parsing the Anthropic API response"
          }),
          { status: 500 }
        )
      }
    } catch (error: any) {
      console.error("Error calling Anthropic API:", error)
      return new NextResponse(
        JSON.stringify({
          message: "An error occurred while calling the Anthropic API"
        }),
        { status: 500 }
      )
    }
  } catch (error: any) {
    let errorMessage = error.message || "An unexpected error occurred"
    const errorCode = error.status || 500

    if (errorMessage.toLowerCase().includes("api key not found")) {
      errorMessage =
        "Anthropic API Key not found. Please set it in your profile settings."
    } else if (errorCode === 401) {
      errorMessage =
        "Anthropic API Key is incorrect. Please fix it in your profile settings."
    }

    return new NextResponse(JSON.stringify({ message: errorMessage }), {
      status: errorCode
    })
  }
}
