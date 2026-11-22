# KAN-70 integrate the classification and generation pipeline
also KAN-79 loading from supabase instead of local folder

# Takeaways 

* I made significant changes to the way that we map from our sound classification to our instruments in the final beat
* Also we now download sounds from supabase rather than from the local folder.
* Created worker for generating beats and updated relevant endpoints within backend
* Need the sound classification results after user has a chance to override to be saved to the database. 
* With that data saved + the prompt/ parameters we are all set
* Everything should be more or less integrated from there
* Update : Had to make some changes to be compatible with a new PR that popped up during development but functionality should still be the same

Other summary information you feel is important

## Resource Usage

Tool and Model(s) Used: Codex, GPT 6.1 Sol Medium 

Tokens Used & Dollar Equivalent (if using a free tier, specify how much of your allocation was used): 
ChatGPT/Codex/Openai does not easily expose numbers of tokens used. 
Used only 16% of the ChatGPT Plus 5 Hour limit. 

## Chat Log
Link provided for brevity:
https://chatgpt.com/s/cx_6b035571616c8191b81890a41897f15a 
