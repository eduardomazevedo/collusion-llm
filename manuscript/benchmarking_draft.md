Owner: Ioan, second owner: Eduardo.

We are going to benchmark performance of a bunch of different approaches in our test set (Joe / acl).

Have to decide main metric, at most one more other main metric.
  - key problem: joe's data is 0 to 100. acl data is binary.
  - We have to choose ONE way that works for everything, report it in the text, and then report other ways in the appendix.
  - To have only one way, we have to convert Joe's to binary.
  - One approach we report area under ROC curve using the continuous score 0-100. This one I would put in appendix.
  - For main text, just turn the prediction to binary with 75 threshold, and report binary measures: accuracy, precision, recall, F1.
  - Main asset will be table with method | accuracy | precision | recall | F1****** | AUC.
  - Maybe better table is: model (gpt-40) | prompt (SimpleCapacityV8.1.1) | followup queries / agent queries (none) | F1

Have to decide what approaches to put in the benchmark.
  - Things that we will vary:
  - model: let's run some old models to see whether old models do ok.
  - repeated prompts:
        non-interactive approaches: no repetition, repeat 10x regargless and take average
        agentic approaches: repeat 10x only for the positives, follow up queries for positives.
  - Different prompts.

Have to produce assets.
  - Step one is to run these extra queries needed.
  - Today I ran 10x for benchmark prompt with gpt-40.
  - TODOs: run 1x other models.

  - Next step, is python code that uses the database to produce the tables.
  - I would first write a script that produces a dataframe where entries are confusion matrices; save this as pickle or parquet or something.
  - Then another script that writes the nice csv / latex tables.

Have to write.
  - Then write the section.