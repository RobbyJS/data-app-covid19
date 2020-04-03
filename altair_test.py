#%% altair quick test
import altair as alt
from vega_datasets import data

source = data.stocks()

alt.Chart(source).mark_line().encode(
    x='date',
    y='price',
    color='symbol',
).interactive()

# %%
# Transform tests
import altair as alt
import pandas as pd

data = pd.DataFrame({'t': range(101)})

alt.Chart(data).mark_line().encode(
    x='x:Q',
    y='y:Q',
    order='t:Q'
).transform_calculate(
    x='cos(datum.t * PI / 50)',
    y='sin(datum.t * PI / 25)'
)

# %%
from vega_datasets import data
import altair as alt
import numpy as np
source = data.stocks()
source['random'] = np.random.randint(low=1, high=100, size=source.shape[0])
alt.Chart(source).mark_line().encode(
    x='date',
    y='y:Q',
    color='symbol',
).transform_calculate(    
    y='datum.price/datum.random'
).interactive()


