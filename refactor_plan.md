# Intro
This md file is for planning the refactoring of the code and data organization.
The purpose is to start with a plain words plan, refine it with CLAUDE interactively, and then implement it sequentially with tests. 
At the end, we should have a very clean code base, along with explanatory files that explain how everything works and how the code and data are structured.

# Refactoring
We want to refactor the codebase to follow the project workflow that has some parts:
1. setup (the scripts that need to be run if the project is taken from the git repo, so that one can continue working on it, or as a first time user)
2. pre query submission (building necessary intermediate files, asssessing new prompts by running them on transcripts from the testset or simply as a list ,assessing how well they perform versus the test set transcripts, etc)
3. query submissions (scripts related to running prompts on transcripts using LLMs; this includes everything needed to run all available transcripts, or just for the testset, or individually, either submitting the requests individually or using the batch request functionality from OpenAI; this also includes what is needed to run follow up prompts on responses from initial queries, saving everything in the appropriate way in the database, etc); note that for now we only use OpenAI LLMs, but in the future we might want to be able to configure this an duse it with additional models from other providers.
4. post query submissions (once we have a populated queries database, we use it to perform analysis: build benchmarking files, do covariates analysis (this is not implemented yet but will be soon))

# Data organization
We also want to restructure the data folder with some subdirectories:
- datasets (main data files we build from CapIQ, Compustat, any outside source like that, and also the big queries database, the raw human review files, etc)
- intermediaries (files that were built from datasets at any point in the workflow of the project and are used downstream from datasets creation; this sort of file can be updated if we retrieve a new version of a dataset; these files are generally used as a sort of middle step to be able to perform something else later on in the code)
- outputs (files that are created for some sort of analysis and that will later be used to create tables or figures for the paper manuscript)
- cache (files that are temporary, like the batches folder and its json contents when we run a big batch on the full sample of transcripts, individual batch files when we run an individual batch file, database exports simply for visualization, etc.)
- metadata (files that contain data descriptions; we'll try to create these for the existing data once we've established the structure, and every time we create a new data file we should also take the time to make a metadata file so it's very easy to see what data we have without having to open any actual data files)

# Other
Other things to consider, before, during or after the refactoring:
- The assets folder that now has the prompts.json file should perhaps also include a json that includes the relevant information about different LLMs we use and how they need to be used; e.g. we can add in this file for the provider OpenAI, the models we want to use, and for each model we record things we need to know when we use them such as whether they allow structured output, prices for input and completions, and even maybe the correct structure for the request so that we can access it when we revamp the LLM functionalities so we're always sure to do run the queries correctly.
- run the test set (including joe and acl) using a new version of the SimpleCapacityV8.1.1 prompt that also asks specifically for a desired structure of output, with older OpenAI models so that we can run the benchmarking functionality and compare older and newer models on the one off approach to queries.



