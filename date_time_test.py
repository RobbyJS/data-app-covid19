#%%
import pandas as pd

#%%
data = pd.DataFrame({'A':[1,2,3],'B':[2,3,4]})

# %%
data["C"] = ['2020-01-02','2020-01-20','2020-01-02']

# %%
data.dtypes

# %%
data["D"] = pd.to_datetime(data["C"])

# %%
