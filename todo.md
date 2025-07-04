FIGURING OUT BATCHES

**DONE**
In llm module add separate batch related functions:
- DONE! put together batch (given prompt and given transcripts as arguments)
- DONE! upload batch file to openai (given batch as argument)
- DONE! check for updates for a given batch job (manual, not automated on time interval)
- DONE! retrieve and save batch responses of a given batch job AND put the batch responses of a given completed batch job into big queries db

**DONE**
Create a new .sh type script to be able to call the batch related functions in intuitive way.
What I want to be able to do with that wrapper .sh script for batches:
--> all the individual batch related steps for:
- a list of companies (could be one, or many), meaning all their transcripts
- a given prompt name

**DONE**
1. Need a batch size check function that checks if a batch falls within openai limits
OpenAI limits for model gpt-4o-mini:
- max 50,000 requests per batch
- max 40,000,000 input tokens per batch queue (assume one batch at a time)

2. Need a batch cost check function that estimates cost of a batch once it was created.
Takes as input the batch file to calculate cost of input tokens and returns cost estimated using prices for the model we use, the inputs, and for the outputs it takes the maximum we specified for responses (in most cases it will be max 1000 tokens expected for a response of one request)
Prices:
- $0.075 per 1,000,000 input tokens
- $0.3 per 1,000,000 output tokens

**DONE**
Batch group submission: within big_batch_runner.py a function that takes as argument a prompt name and submits batches from the appropriate folder while following rate limits form OpenAI
- go through all jsonl batches in batch folder (named like the prompt name and "_batches" in output folder) and extract all transcript ids from custom_id (e.g. from "custom_id": "request-94097" get transcriptid 94097)
- for each transcriptid get its number of tokens from transcript-tokens.csv located in data folder
- make a dataframe batch_tracker that records the following for each batch file:
- record for each batch the total input tokens
- record for each batch the estimated input cost (using token size of the given prompt times the number of requests in the batch file, and the token sizes of each transcript corresponding to each request within the batch); price is $0.075 per 1,000,000 input tokens
- record for each batch the estimated output cost (average of 250 reponse tokens expected per request, maximum is imposed to 500 tokens per request, so total for a batch multiplies this with number of requests in the batch); price is $0.3 per 1,000,000 output tokens
- add "batch_id", "status", "completed_requests", "failed_requests", "total_requests" all of them initially empty and they will be populated later
- loop through all batches in the dataframe and submit them one by one as long as the total size of the batch queue is at most 35,000,000 input tokens
- here we need a helper function that updates the tracker dataframe to determine if we can submit a batch; the batch queue is made of all transcripts that were submitted; the available tokens should be calculated whenever we add a batch as 35,000,000 minus the current_queue_size which counts for all batches that have "status" as "in_progress"; we add a batch if the batch size is less than that difference; if we can't add the next batch, pause and wait 5 minutes and then check again
- whenever we submit a batch or we check queue size and wait because the queue is full, we also update the dataframe to reflect the current state of transcripts (which either has a value like "in_progress" or "completed" or nothing yet)
- if we stop the code or it breaks for whatever reason, we want to be able to attempt batch submission again, and when we do, we check if the tracking dataframe exists and what the current state of it is, so that we carry on from where we left off (e.g. if I need to disconnect and take my laptop somewhere else and continue the batch submission)

**DONE**
Helper functionalities:
- DONE! output from the capiq feather all individual companies (with names) and their respective transcript ids (with headlines, only most recent)
- DONE! prepare the transcripts retrieved with capiq.get_transcripts(transcript_ids) to be passed to LLM; They are initially in a JSON schema; We want them as a text that shows all call contributions separated by new lines
transcriptcomponenttypename from speakertypename: componenttext


----
**DONE**
Workflow to process ALL available comapnies and transcripts from capiq, given a prompt:
- add companies as individual batches one by one to stay within limit (i.e. using limit check function)
- a function creates a small separate file to keep track of these batches
- we submit the batches one by one (i.e. submit, wait to complete, save responses to the big database, go to the next one until out of batches)

----


**DONE**
DONE! Clean up the duplicates (other than the query id and timestamp, some of the entries are exact duplicates added by mistake multiple times; only most recent one should be kept)
DONE! Re save all completed batches (change indicator to FALSE) to include ones that weren't saved initially due to JSON structure mismatch
DONE! Re attempt failed batches (clear out the failed)

Let code run to get big batch responses

**TO DO A BIT LATER**
Sign up for google cloud compute and implement remote run and monitor procedure for batches.

**DONE**
Reorganizing the queries database and refactoring the query save procedure
- Set LLM_provider, model, temperature, max_response_tokens when we make individual or batch requests to some default that can be easily modified in the code and also referenced when we store the request metadata
- Add metadata at request level
    - LLM provider (e.g. "openai")
    - model (e.g. "gpt-4o-mini")
    - whether individual API call or part of batch (e.g. "single" or "batch")
    - temperature (e.g. 1)
    - max resonse tokens (e.g. 500)
- Add metadata at response level
    - for "single" case: from the response object, in "usage", take "input_tokens" and "output_tokens"
    - for the "batch" case: from  response object (i.e. each line of the response file), in "usage", take "prompt_tokens" and "completion_tokens" (note: these are the same as the single request case input_tokens and output_tokens respectively)

**TO DO AT THE END OF BIG BATCH RUN**
- Sweep for missing transcripts in batch processing and request them with synchronous API

------------------------------------------------------------------------------------------------------------------------------

FIGURING OUT FALSE POSITIVES

**DONE** Idea 1 (Eduardo to implement): get 10 samples from top hits; top scorer based on score from first time the prompt was run on a given transcript

Idea 2: chunks (later, more tedious; need to decide how fancy we want to be)

**DONE** Idea 3: second LLM call (Ioan to implement)
- on excerpts, says whether it’s indeed collusive (need a new table that references the query id of the original table, but all other identifying stuff shouldn’t be repeated)

------------------------------------------------------------------------------------------------------------------------------

Running the prompt SimpleCapacityV8.1.1 1x on joe and acl test sample using other models from openai for benchmarking
Models:
gpt-3.5-turbo-0125 (0.5/M input) --> doesn't support structured output
gpt-4o-mini-2024-07-18 (0.15/M input)
gpt-4.1-nano-2025-04-14 (0.1/M input) DONE
gpt-4.1-mini-2025-04-14 (0.4/M input) DONE
o4-mini-2025-04-16 (1.1/M input) almost DONE


Considerations:
- in create_leaderboard.py instead of simply loading the responses as json and extrracting score, try that first, but if we can't read the json because it doesn't have valid json format, use utils function extract_invalid_response and take the score value from that
- add another function in create_leaderboard.py called calculate_F1 similar to the functions that calculate accuracies; this function should returns the F1 score based on the recall and precision of the LLM response score versus the test sample values (using )


