# Third-Party Licenses

This project depends on the following third-party software. Full license texts are in [`LICENSES/`](LICENSES/).

## Runtime dependencies

| Package | Version | License | Source |
| :--- | :--- | :--- | :--- |
| piper-tts | >=1.4.2 | GPL-3.0 | https://github.com/OHF-Voice/piper1-gpl |
| fastapi | >=0.136.3 | MIT | https://github.com/fastapi/fastapi |
| uvicorn | >=0.47.0 | BSD-3-Clause | https://github.com/encode/uvicorn |
| pydantic | >=2.13.3 | MIT | https://github.com/pydantic/pydantic |
| langdetect | >=1.0.9 | Apache-2.0 | https://github.com/Mimino666/langdetect |
| trafilatura | >=2.0.0 | Apache-2.0 | https://github.com/adbar/trafilatura |
| onnxruntime | (transitive, via piper-tts) | MIT | https://github.com/microsoft/onnxruntime |

## Voice models

Voice models are **not** bundled with this project and are **not** covered by its GPL-3.0 license. They are downloaded separately by the user and are governed by their own licenses, which vary per voice. See the "Voice models are licensed separately" section in `README.md` for details, and consult the `MODEL_CARD` file for each voice at:

https://huggingface.co/rhasspy/piper-voices