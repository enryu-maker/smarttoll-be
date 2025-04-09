from fastapi import APIRouter
import os
import subprocess
router = APIRouter(
    prefix="/v1/stream",
    tags=["V1 TOLL STREAM API"],
)

STREAMS_DIR = "streams"
os.makedirs(STREAMS_DIR, exist_ok=True)


@router.get("/start_stream/")
def start_stream(rtsp_url: str, stream_name: str):
    """
    Starts an FFmpeg process to convert RTSP to HLS.
    Example API Call:
    http://localhost:8000/v1/stream/start_stream/?rtsp_url=rtsp://admin:123456@206.84.233.93:8001/stream1&stream_name=stream1
    """
    hls_path = os.path.join(STREAMS_DIR, stream_name)
    os.makedirs(hls_path, exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg", "-i", rtsp_url, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-f", "hls", "-hls_time", "2", "-hls_list_size", "4",
        "-hls_flags", "delete_segments", f"{hls_path}/stream.m3u8"
    ]

    try:
        process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"FFmpeg failed: {stderr.decode()}")
            return {"message": "Failed to start stream", "error": stderr.decode()}

        return {"message": "Streaming started!", "hls_url": f"http://103.194.228.109:8000/streams/{stream_name}/stream.m3u8"}

    except Exception as e:
        return {"message": "Error starting stream", "error": str(e)}
