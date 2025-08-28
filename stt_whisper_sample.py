import asyncio
from openai import OpenAI, AsyncOpenAI


def sync_openai(audio_path: str, client: OpenAI):
    """
    Perform synchronous transcription using OpenAI-compatible API.
    """
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="stt_model",
            language="ms",
            response_format="json",
            temperature=0.0,
            extra_body=dict(
                seed=4419,
                repetition_penalty=1.3,
            ),
        )
        print("transcription result:", transcription.text)


async def stream_openai_response(audio_path: str, client: AsyncOpenAI):
    """
    Perform asynchronous (streaming) transcription.
    """
    print("\ntranscription result:", end=" ")
    with open(audio_path, "rb") as f:
        transcription = await client.audio.transcriptions.create(
            file=f,
            model="stt_model",
            language="ms",
            response_format="json",
            temperature=0.0,
            extra_body=dict(
                seed=420,
                top_p=0.6,
            ),
            stream=True,
        )
        async for chunk in transcription:
            if chunk.choices:
                content = chunk.choices[0].get("delta", {}).get("content")
                if content:
                    print(content, end="", flush=True)
    print()


def main():
    audio_path = "output.mp3"  # You can switch to .m4a as needed

    # Modify OpenAI's API base to use your vLLM server
    openai_api_key = "EMPTY"
    openai_api_base = "http://localhost:9801/v1"

    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
    )
    sync_openai(audio_path, client)

    async_client = AsyncOpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
    )
    asyncio.run(stream_openai_response(audio_path, async_client))


if __name__ == "__main__":
    main()
