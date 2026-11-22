
# Write this up 
# Clean it up for commit and merge. Sync on the Yamnet classification.


# Rebuild the music gen pipeline setup for backend integration

## Main takeaways (You must write this section manually and without AI assistance. The purpose is for you to reflect on what you did and practice articulating that for others.)
-Through a combination of Musicgen with YourMT3+, and HDemucs we can create a better musical product for the user than simply through the use of fermata. 
-Endpoints are established for calling on the pattern generation and synthesis capabilities of the musicgen pipeline. 
-The generic endpoint does not make use of HDemucs.
-Splitting the audio streams with HDemucs improved the performance of percussive translation
-Examples of the output are shown in outputs folder. Usually under the name everyday_smoothed.wav. This corresponds to everyday sounds and performing audio smoothing/ balancing before using the midi velocities.
-The most common fault in the pipeline was audio transcription
-Failure to properly translate can lead to significant missing portions of the original beat. 
-YourMT3+ is a different service from muscriptor as muscriptor had a licensing agreement which may not align with out usage.




## Resource Usage

ChatGPT / Codex was used as the AI tool

Tokens Used & Dollar Equivalent:
ChatGPT doesn't offer native support for token/ dollar equivalent usage amount. 
I do have ChatGPT plus as part of a free program for students. Codex was at about half of its 5 hour usage limit. 
I did not reach any usage limits though. 

## Chat Log

Codex Chat: https://chatgpt.com/s/cx_6af507cda03481919797b9d737a00403 
Other Codex chat (From testing separate audio streams): 
https://chatgpt.com/s/cx_6af507e37b6c8191833337eb536152bc
