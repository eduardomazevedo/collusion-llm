FIGURING OUT BATCHES

In llm module add separate batch related functions:
- put together batch (given prompt and given transcripts as arguments)
- upload batch file to openai (given batch as argument)
- check for updates for a given batch job (manual, not automated on time interval)
- download and save batch responses of a given batch job
- put the batch responses of a given completed batch job into big queries db

Create a new .sh type script to be able to call the batch related functions in intuitive way.
What I want to be able to do with that wrapper .sh script for batches:
--> all the individual batch related steps for:
- a list of companies (could be one, or many), meaning all their transcripts
- a given prompt name

Extra checks to put in place:

1. Need a batch size check function that checks if a batch falls within openai limits
OpenAI limits for model gpt-4o-mini:
- max 50,000 requests per batch
- max 40,000,000 input tokens per batch queue (assume one batch at a time)

2. Need a batch cost check function that estimates cost of a batch once it was created.
Takes as input the batch file to calculate cost of input tokens and returns cost estimated using prices for the model we use, the inputs, and for the outputs it takes the maximum we specified for responses (in most cases it will be max 1000 tokens expected for a response of one request)
Prices:
- $0.075 per 1,000,000 input tokens
- $0.3 per 1,000,000 output tokens

Helper functionalities:
- DONE! output from the capiq feather all individual companies (with names) and their respective transcript ids (with headlines, only most recent)
- prepare the transcripts retrieved with capiq.get_transcripts(transcript_ids) to be passed to LLM; They are initially in a JSON schema; We want them as a text that shows all call contributions separated by new lines
transcriptcomponenttypename from speakertypename: componenttext


----
LATER (i.e. once the above works well)
Workflow to process ALL available comapnies and transcripts from capiq, given a prompt:
- add companies to batches one by one to stay within limit (i.e. using limit check function)
- a function creates a small separate file to keep track of these batches
- we submit the batches one by one (i.e. submit, wait to complete, save responses to the big database, go to the next one until out of batches)



