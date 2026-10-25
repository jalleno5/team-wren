# YAMNet Sound Classification & Evaluation

## Main takeaways (You must write this section manually and without AI assistance. The purpose is for you to reflect on what you did and practice articulating that for others.)
- YAMNet setup: Used TensorFlow’s official YAMNet tutorial notebook as the template, then added my own recordings and tests.
- Dataset collection: Recorded 31 sounds across 10 categories, with 3 takes of each (2 being ~3 seconds, 1 being ~1 second) plus one mixed-noise water recording.
- Audio preprocessing: Converted the M4A files to 16 kHz mono WAV with FFmpeg (the format YAMNet needs).
- Batch testing: Ran all 31 recordings through YAMNet and saved the top 3 labels and scores for each to a CSV file.
- Results: The correct label was the top prediction for 7 of 30 recordings (23.3%) and in the top 3 for 13 of 30 (43.3%). Only 3 of 10 sound types got the same top label across their first 2 takes.
- Limitations: YAMNet struggled with keys, clapping, and pen clicks. Not yet tested: sub-second clips (mine ran 1.07 to 4.35 seconds), other devices for recording sounds, and how well labels map to musical roles.
- Deliverables: Completed notebook, results CSV, and the shared recordings.

## Resource Usage

Tool and Model(s) Used: ChatGPT (GPT-6)
- Purpose: Since the project used a pre-existing YAMNet tutorial/template, my main work involved recording audio samples, writing test functions for batch evaluation, and analyzing the model's predictions. ChatGPT provided feedback on notebook organization, code correctness, testing results, conclusions, and reproducibility, and helped identify issues to address before submitting the notebook to GitHub.
- Tokens Used & Dollar Equivalent: Exact token usage unavailable. Used ChatGPT with no additional per-request or API charges.

## Chat Log
https://chatgpt.com/share/6ade3725-4b2c-83e9-8f14-2948588841f4
