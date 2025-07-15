import { checkApiKey, getServerProfile } from "@/lib/server/server-chat-helpers"
import { ChatSettings } from "@/types"
import { GoogleGenerativeAI } from "@google/generative-ai"
import { getMCPTools, executeMCPTool } from "@/lib/mcp/mcp-integration"

// export const runtime = "edge"

export async function POST(request: Request) {
  const json = await request.json()
  const { chatSettings, messages, selectedTools } = json as {
    chatSettings: ChatSettings
    messages: any[]
    selectedTools: any[]
  }

  try {
    const profile = await getServerProfile()

    checkApiKey(profile.google_gemini_api_key, "Google")

    const genAI = new GoogleGenerativeAI(profile.google_gemini_api_key || "")
    
    // Get MCP tools and convert to Google format
    const mcpTools = await getMCPTools()
    console.log('MCP Tools found:', mcpTools.length, mcpTools.map(t => t.function?.name))
    
    const googleTools = mcpTools.map(tool => ({
      functionDeclaration: {
        name: tool.function.name,
        description: tool.function.description,
        parameters: tool.function.parameters
      }
    }))

    const googleModel = genAI.getGenerativeModel({ 
      model: chatSettings.model,
      tools: googleTools.length > 0 ? [{ functionDeclarations: googleTools.map(t => t.functionDeclaration) }] : undefined
    })

    const lastMessage = messages.pop()

    const chat = googleModel.startChat({
      history: messages,
      generationConfig: {
        temperature: chatSettings.temperature
      }
    })

    const response = await chat.sendMessage(lastMessage.parts)
    
    // Check for function calls
    const functionCalls = response.response.candidates?.[0]?.content?.parts?.filter(part => part.functionCall) || []
    
    if (functionCalls.length > 0) {
      // Execute function calls
      const functionResults = []
      
      for (const call of functionCalls) {
        const functionName = call.functionCall.name
        const args = call.functionCall.args
        
        // Handle both firecrawl and columbia-lake-agents tools
        if (functionName.startsWith('firecrawl_') || functionName.startsWith('columbia-lake-agents_')) {
          try {
            const result = await executeMCPTool(functionName, args)
            functionResults.push({
              functionResponse: {
                name: functionName,
                response: result
              }
            })
          } catch (error) {
            functionResults.push({
              functionResponse: {
                name: functionName,
                response: { error: error.message }
              }
            })
          }
        }
      }
      
      // Send function results back to model
      const finalResponse = await chat.sendMessage(functionResults)
      
      const encoder = new TextEncoder()
      const text = finalResponse.response.text()
      return new Response(encoder.encode(text), {
        headers: { "Content-Type": "text/plain" }
      })
    }

    // Regular response without function calls
    const streamResponse = await chat.sendMessageStream(lastMessage.parts)

    const encoder = new TextEncoder()
    const readableStream = new ReadableStream({
      async start(controller) {
        for await (const chunk of streamResponse.stream) {
          const chunkText = chunk.text()
          controller.enqueue(encoder.encode(chunkText))
        }
        controller.close()
      }
    })

    return new Response(readableStream, {
      headers: { "Content-Type": "text/plain" }
    })

  } catch (error: any) {
    let errorMessage = error.message || "An unexpected error occurred"
    const errorCode = error.status || 500

    if (errorMessage.toLowerCase().includes("api key not found")) {
      errorMessage =
        "Google Gemini API Key not found. Please set it in your profile settings."
    } else if (errorMessage.toLowerCase().includes("api key not valid")) {
      errorMessage =
        "Google Gemini API Key is incorrect. Please fix it in your profile settings."
    }

    return new Response(JSON.stringify({ message: errorMessage }), {
      status: errorCode
    })
  }
}
