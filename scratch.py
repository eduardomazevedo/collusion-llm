#%%
import pandas as pd
import modules.capiq as capiq


#%%
print(capiq.get_transcripts([23993]))
# %%
print(capiq.get_transcripts([23993, 23994]))
# %%
print(capiq.get_single_transcript(23993))
# %%
print(capiq.get_single_transcript(23994))
# %%
