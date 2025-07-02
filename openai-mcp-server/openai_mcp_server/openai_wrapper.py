# openai-mcp-server/openai_mcp_server/openai_wrapper.py
import os
import base64
import uuid
import httpx
from pathlib import Path
from openai import OpenAI, APIError, RateLimitError
from typing import List, Dict, Optional, Any, Literal
from ascii_colors import ASCIIColors, trace_exception

try:
    client = OpenAI()
except Exception as e:
    ASCIIColors.error(f"Failed to initialize OpenAI client. Ensure OPENAI_API_KEY is set and valid: {e}")
    client = None

DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
DEFAULT_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
DEFAULT_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
DEFAULT_DALLE_MODEL = os.getenv("OPENAI_DALLE_MODEL", "dall-e-3")
DEFAULT_DALLE_IMAGE_SIZE_D3 = os.getenv("OPENAI_DALLE_IMAGE_SIZE_D3", "1024x1024")
DEFAULT_DALLE_IMAGE_SIZE_D2 = os.getenv("OPENAI_DALLE_IMAGE_SIZE_D2", "1024x1024")


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
            messages=messages,
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
    
    current_speed = speed if speed is not None else 1.0
    if not (0.25 <= current_speed <= 4.0):
        return {"error": "Invalid speed value. Must be between 0.25 and 4.0."}

    ASCIIColors.info(f"OpenAI Wrapper: Requesting TTS for text '{input_text[:30]}...' using model '{selected_model}', voice '{selected_voice}'.")
    try:
        response = client.audio.speech.create(
            model=selected_model,
            voice=selected_voice,
            input=input_text,
            response_format=response_format,
            speed=current_speed
        )
        
        audio_bytes = response.content

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
        return {"error": f"Unexpected error with OpenAI TTS: {str(e)}"}

async def generate_dalle_image(
    prompt: str,
    public_dir: Path,
    file_server_base_url: str,
    model: Optional[str] = None,
    n: int = 1,
    quality: Literal["standard", "hd"] = "standard",
    response_format: Literal["url", "b64_json"] = "url",
    size: Optional[str] = None,
    style: Literal["vivid", "natural"] = "vivid"
) -> Dict[str, Any]:
    if not client:
        return {"error": "OpenAI client not initialized. Check API key."}

    selected_model = model if model else DEFAULT_DALLE_MODEL

    if selected_model == "dall-e-3" and n != 1:
        ASCIIColors.warning("DALL-E 3 currently supports generating 1 image at a time (n=1). Setting n=1.")
        n = 1
    elif selected_model == "dall-e-2" and not (1 <= n <= 10):
        return {"error": "For DALL-E 2, 'n' (number of images) must be between 1 and 10."}

    selected_size = size
    if not selected_size:
        selected_size = DEFAULT_DALLE_IMAGE_SIZE_D3 if selected_model == "dall-e-3" else DEFAULT_DALLE_IMAGE_SIZE_D2

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
            "response_format": "url",
            "size": selected_size,
        }
        if selected_model == "dall-e-3":
            api_params["quality"] = quality
            api_params["style"] = style
        
        response = await client.images.generate(**api_params)

        images_data = []
        async with httpx.AsyncClient() as http_client:
            for img in response.data:
                if not img.url:
                    continue

                download_response = await http_client.get(img.url)
                download_response.raise_for_status()
                image_bytes = download_response.content

                filename = f"{uuid.uuid4()}.png"
                file_path = public_dir / filename
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                
                if response_format == "url":
                    local_url = f"{file_server_base_url}/images/{filename}"
                    images_data.append({"url": local_url, "revised_prompt": img.revised_prompt})
                elif response_format == "b64_json":
                    b64_content = base64.b64encode(image_bytes).decode('utf-8')
                    images_data.append({"b64_json": b64_content, "revised_prompt": img.revised_prompt})

        ASCIIColors.green(f"OpenAI Wrapper: DALL-E image(s) downloaded and processed ({len(images_data)} images).")
        return {"images": images_data, "model_used": selected_model}

    except httpx.HTTPStatusError as e:
        ASCIIColors.error(f"Failed to download image from OpenAI URL: {e.request.url} - Status {e.response.status_code}")
        return {"error": f"Failed to download image from OpenAI URL: {e.request.url}"}
    except APIError as e:
        return {"error": f"OpenAI DALL-E API Error: {e.message}", "status_code": e.status_code}
    except RateLimitError as e:
        return {"error": f"OpenAI DALL-E Rate Limit Error: {e.message}"}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Unexpected error with OpenAI DALL-E: {str(e)}"}