# openai-mcp-server/openai_mcp_server/openai_wrapper.py
import os
import base64 # For encoding TTS audio
from openai import OpenAI, APIError, RateLimitError
from typing import List, Dict, Optional, Any, Literal # Literal for specific choices
from ascii_colors import ASCIIColors, trace_exception # Assuming you have trace_exception

# Initialize the OpenAI client
try:
    client = OpenAI()
except Exception as e:
    ASCIIColors.error(f"Failed to initialize OpenAI client. Ensure OPENAI_API_KEY is set and valid: {e}")
    client = None

DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
DEFAULT_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1") # Available: tts-1, tts-1-hd
DEFAULT_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy") # Available: alloy, echo, fable, onyx, nova, shimmer
DEFAULT_DALLE_MODEL = os.getenv("OPENAI_DALLE_MODEL", "dall-e-3") # Available: dall-e-2, dall-e-3
DEFAULT_DALLE_IMAGE_SIZE_D3 = os.getenv("OPENAI_DALLE_IMAGE_SIZE_D3", "1024x1024") # dall-e-3 sizes
DEFAULT_DALLE_IMAGE_SIZE_D2 = os.getenv("OPENAI_DALLE_IMAGE_SIZE_D2", "1024x1024") # dall-e-2 sizes


async def generate_chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = 1500,
    **kwargs
) -> Dict[str, Any]:
    if not client:
        return {"error": "OpenAI client not initialized. Check API key and logs."}
    selected_model = model if model else DEFAULT_CHAT_MODEL
    ASCIIColors.info(f"OpenAI Wrapper: Requesting chat completion from model '{selected_model}'...")
    try:
        completion = await client.chat.completions.create(
            model=selected_model,
            messages=messages, # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        if completion.choices and completion.choices[0].message:
            content = completion.choices[0].message.content
            finish_reason = completion.choices[0].finish_reason
            usage = completion.usage
            ASCIIColors.green(f"OpenAI Wrapper: Chat completion received. Finish reason: {finish_reason}")
            return {
                "content": content,
                "finish_reason": finish_reason,
                "model_used": selected_model,
                "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens, "total_tokens": usage.total_tokens } if usage else None
            }
        else:
            return {"error": "No content in completion response from OpenAI."}
    except APIError as e: return {"error": f"OpenAI API Error: {e.message}", "status_code": e.status_code}
    except RateLimitError as e: return {"error": f"OpenAI Rate Limit Error: {e.message}"}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Unexpected error with OpenAI chat: {str(e)}"}

async def generate_tts_audio(
    input_text: str,
    model: Optional[str] = None,
    voice: Optional[str] = None,
    response_format: Literal["mp3", "opus", "aac", "flac"] = "mp3",
    speed: Optional[float] = 1.0
) -> Dict[str, Any]:
    if not client:
        return {"error": "OpenAI client is not initialized. Check API key and server startup logs."}
    
    selected_model = model if model else DEFAULT_TTS_MODEL
    selected_voice = voice if voice else DEFAULT_TTS_VOICE
    
    current_speed = speed if speed is not None else 1.0 # Use a local var for clarity
    if not (0.25 <= current_speed <= 4.0):
        return {"error": "Invalid speed value. Must be between 0.25 and 4.0."}

    ASCIIColors.info(f"OpenAI Wrapper: Requesting TTS for text '{input_text[:30]}...' using model '{selected_model}', voice '{selected_voice}'.")
    try:
        # client.audio.speech.create makes an HTTP request and returns an httpx.Response
        response = client.audio.speech.create( # This line makes the API call
            model=selected_model,
            voice=selected_voice, # type: ignore
            input=input_text,
            response_format=response_format,
            speed=current_speed
        )
        
        # The response object from a non-streaming binary request like this
        # will have its content available directly after the await.
        # The `response` is an `openai.Stream` which is an `httpx.Response`.
        # We need to get the raw bytes.
        
        # The most direct way to get bytes from an httpx.Response is response.content
        # However, since the API call was awaited, the response should be fully received.
        # The openai.Stream object might offer a more specific way.
        # Let's try using the stream_to_file method to a BytesIO buffer if direct content access is tricky,
        # or check if response.read() for non-streaming completed responses works.

        # According to OpenAI SDK, for non-streaming audio, `response.read()` should give bytes
        # or you can use `response.content` if you are sure it's fully loaded.
        # Since `client.audio.speech.create` is awaited, the response should be complete.
        audio_bytes = response.content # This should be the raw bytes of the audio file

        if not audio_bytes:
            ASCIIColors.error("OpenAI Wrapper: TTS audio response content is empty.")
            return {"error": "TTS audio response content is empty from OpenAI."}
            
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        ASCIIColors.green(f"OpenAI Wrapper: TTS audio generated and base64 encoded ({len(audio_base64)} chars). Format: {response_format}")
        return {
            "audio_base64": audio_base64,
            "format": response_format,
            "model_used": selected_model,
            "voice_used": selected_voice
        }
    except APIError as e:
        ASCIIColors.error(f"OpenAI TTS API Error: {e.message} (Status: {e.status_code})", exc_info=True)
        return {"error": f"OpenAI TTS API Error: {e.message}", "status_code": e.status_code}
    except RateLimitError as e:
        ASCIIColors.error(f"OpenAI TTS Rate Limit Error: {e.message}", exc_info=True)
        return {"error": f"OpenAI TTS Rate Limit Error: {e.message}"}
    except Exception as e:
        ASCIIColors.error(f"Unexpected error with OpenAI TTS: {str(e)}", exc_info=True)
        # trace_exception(e) # Use this if logger isn't capturing traceback well enough
        return {"error": f"Unexpected error with OpenAI TTS: {str(e)}"}

async def generate_dalle_image(
    prompt: str,
    model: Optional[str] = None,
    n: int = 1, # Number of images to generate (dall-e-2: 1-10, dall-e-3: 1)
    quality: Literal["standard", "hd"] = "standard", # For dall-e-3
    response_format: Literal["url", "b64_json"] = "url",
    size: Optional[str] = None, # e.g., "1024x1024", "1792x1024", etc.
    style: Literal["vivid", "natural"] = "vivid" # For dall-e-3
) -> Dict[str, Any]:
    if not client:
        return {"error": "OpenAI client not initialized. Check API key."}

    selected_model = model if model else DEFAULT_DALLE_MODEL

    # Validate n based on model
    if selected_model == "dall-e-3" and n != 1:
        ASCIIColors.warning("DALL-E 3 currently supports generating 1 image at a time (n=1). Setting n=1.")
        n = 1
    elif selected_model == "dall-e-2" and not (1 <= n <= 10):
        return {"error": "For DALL-E 2, 'n' (number of images) must be between 1 and 10."}


    # Determine default size based on model if not provided
    selected_size = size
    if not selected_size:
        selected_size = DEFAULT_DALLE_IMAGE_SIZE_D3 if selected_model == "dall-e-3" else DEFAULT_DALLE_IMAGE_SIZE_D2

    # Validate image sizes (OpenAI Python library usually handles this, but good to be aware)
    # DALL-E 3: 1024x1024, 1792x1024, 1024x1792
    # DALL-E 2: 256x256, 512x512, 1024x1024
    valid_sizes_d3 = ["1024x1024", "1792x1024", "1024x1792"]
    valid_sizes_d2 = ["256x256", "512x512", "1024x1024"]

    if selected_model == "dall-e-3" and selected_size not in valid_sizes_d3:
        return {"error": f"Invalid size '{selected_size}' for DALL-E 3. Valid sizes: {valid_sizes_d3}"}
    if selected_model == "dall-e-2" and selected_size not in valid_sizes_d2:
        return {"error": f"Invalid size '{selected_size}' for DALL-E 2. Valid sizes: {valid_sizes_d2}"}


    ASCIIColors.info(f"OpenAI Wrapper: Requesting DALL-E image generation for prompt '{prompt[:50]}...' using model '{selected_model}'.")
    try:
        api_params = {
            "model": selected_model,
            "prompt": prompt,
            "n": n,
            "response_format": response_format,
            "size": selected_size,
        }
        if selected_model == "dall-e-3":
            api_params["quality"] = quality
            api_params["style"] = style
        
        response = client.images.generate(**api_params) # type: ignore

        images_data = []
        for img in response.data:
            if response_format == "url" and img.url:
                images_data.append({"url": img.url, "revised_prompt": img.revised_prompt})
            elif response_format == "b64_json" and img.b64_json:
                images_data.append({"b64_json": img.b64_json, "revised_prompt": img.revised_prompt})
        
        ASCIIColors.green(f"OpenAI Wrapper: DALL-E image(s) data received ({len(images_data)} images).")
        return {
            "images": images_data,
            "model_used": selected_model
        }
    except APIError as e: return {"error": f"OpenAI DALL-E API Error: {e.message}", "status_code": e.status_code}
    except RateLimitError as e: return {"error": f"OpenAI DALL-E Rate Limit Error: {e.message}"}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Unexpected error with OpenAI DALL-E: {str(e)}"}