# Classify Endpoint

## Main takeaways (You must write this section manually and without AI assistance. The purpose is for you to reflect on what you did and practice articulating that for others.)
- Built a FastAPI endpoint to wrap the YAMNet 5-role classification pipeline so the Node backend can call it
- Two routes: file upload for direct testing, URL-based for Supabase signed links which is how our backend actually serves audio
- Tested locally with uvicorn and curl before pushing.

## Resource Usage

Tool and Model(s) Used: Claude Opus 4.5
Tokens Used & Dollar Equivalent: Claude Pro, did not reach usage limits.

## Chat Log

https://claude.ai/share/aeaf0f76-d9a9-45e5-8d3c-39d55fc68239