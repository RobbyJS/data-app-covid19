#%%
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
import time

from math import ceil, floor, log10
from vega_datasets import data as vg_data

from altair import datum
from typing import Tuple

URL_OPENCOVID19 = "https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/final_data/dataCOVID19_es.csv"
url_pop_ccaa = "https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/info_data/Poblaci%C3%B3nCCAA.csv"

url_intern_root = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/"
time_series_path = "csse_covid_19_time_series/" 
url_inter_conf = url_intern_root+time_series_path+"time_series_covid19_confirmed_global.csv"
url_inter_death = url_intern_root+time_series_path+"time_series_covid19_deaths_global.csv"
url_inter_recov = url_intern_root+time_series_path+"time_series_covid19_recovered_global.csv"
url_cov_country_codes = url_intern_root+"UID_ISO_FIPS_LookUp_Table.csv"

world_json = "https://raw.githubusercontent.com/deldersveld/topojson/master/world-countries-sans-antarctica.json"
#url_intern_pop = "https://raw.githubusercontent.com/datasets/population/master/data/population.csv"

# make title
st.title("DataViz App Covid-19 🦠")


#%% Truncate function
def truncate_10(n,up_down):
    temp = floor(log10(n))
    if up_down == "up":
        round_op = lambda x: ceil(x)
    else:
        round_op = lambda x: floor(x)

    return float(round_op(n/10**temp)*(10**temp))

#%% Variables necessary to functions below
col_name_global = 'Country_total'
#%%
@st.cache
def intern_data_ops(df,value_df):
    """Set of operations that are necessary on the three files containing the international data"""
    # Drop unnecessary columns
    col_list_rm = [0,2,3]
    col_list_rm = df.columns.values[col_list_rm]
    df.drop(col_list_rm,axis=1,inplace=True)
    df = df.groupby("Country/Region",as_index=False).sum()
    dates_st = 1
    dates_cols = df.columns.values[dates_st:]
    df = pd.melt(
        df,
        id_vars = ["Country/Region"],
        value_vars = dates_cols,
        var_name = "Date",
        value_name = value_df
    )
    #renames?
    
    return df
#%%
def get_data(which_data='World') -> Tuple[pd.DataFrame]:
    """
    1 - Get data from opencovid19 repository
    2 - Transform raw data into dataframe
    3 - Returns df_covid19_fr (columns = ['date', 'type', 'nombre']) and
                df_covid19_region (columns = ['date', 'maille_nom', 'cas_confirmes', 'deces', 'delta_deces',
                                              'delta_cas_confirmes', 'fatality_rate', 'days_after_5_deaths',
                                               'days_after_50_confirmed']) 
    """
    global region_title
    if which_data == 'World':
        region_title = "Country"
        col_names = list(["Country/Region","Date"])
        data = intern_data_ops(pd.read_csv(url_inter_conf),"Confirmed")
        data = data.merge(
            intern_data_ops(pd.read_csv(url_inter_death),"Deaths"),
            on=col_names,
            how='inner'
            )
        data = data.merge(
            intern_data_ops(pd.read_csv(url_inter_recov),"Recovered"),
            on=col_names,
            how='inner')       
        col_names=['month','day','year']
        data[col_names] = data.Date.str.split("/",expand=True) 
        data["year"] = data["year"].astype(int)+2000
        # data["day"] = data["day"].map('${:,.2f}'.format)
        data["Date"] = data["year"].astype(str)+"-"+data["month"]+"-"+data["day"]
        # We remove the unnecessary columns
        data.drop(col_names,axis=1,inplace=True)        
        data.rename(columns={"Country/Region":region_title},inplace=True)
        #%% Now we load the country codes
        df_codes = pd.read_csv(url_cov_country_codes)
        df_codes.rename(columns={"Country_Region":region_title,"iso3":"Country Code"},inplace=True)
        # keep only rows for which the "combined key" = "Country". That leaves only the row
        # that gathers all data for a country
        mask_countries = np.where(df_codes[region_title] == df_codes['Combined_Key']
                            , True, False)
        df_codes = df_codes[mask_countries]
        # And we add the population column to COVID data by merge operation
        data = data.merge(df_codes[[region_title,'Population','Lat', 'Long_']],how="left")
        # I need a column with the new cases
            # compute delta_cas_confirmes by making the diff between rows on cas_confirmes grouped by region
        data["New_cases"] = data.groupby(region_title)["Confirmed"].diff()
        # Coming out of this condition I have the data df which contains: 
        # Index(['Country', 'Date', 'Confirmed', 'Deaths', 'Recovered', 'Population','New_cases'], dtype='object')
        # I need the same for Spain data. Except maybe for 'Country' == "CCAA"


    else:
        region_title = "CCAA"
        # 1 - Get COVID data
        data = pd.read_csv(URL_OPENCOVID19)        
        data.rename(columns={"muertes":"Deaths","fecha":"Date","curados":"Recovered","casos":"Confirmed","nuevos":"New_cases"},
                    inplace=True)       


        # 2 - Get regions population data
        df_regions = pd.read_csv(url_pop_ccaa)
        df_regions.rename(columns={"Población":"Population"},
                    inplace=True) 
        # add population information
        data = data.merge(df_regions,on=region_title,how='inner')
        # 3 - Calculate the data for the whole country 
        col_idx = list(range(0,data.shape[1]))
        df_covid19_es = data.iloc[:,col_idx].groupby(['Date'],as_index=False).sum()        
        df_covid19_es[region_title] = col_name_global
        df_covid19_es = df_covid19_es.fillna(value=0)

        data = data.append(df_covid19_es,ignore_index=True)
        # 4 - Remove unnecessary columns
        data.drop(['IA','Densidad'],axis=1,inplace=True)
        del df_covid19_es
    
    return data

#%%
scope = st.sidebar.selectbox("Scope of Analysis:", ("World","Spain"))
#scope = "World"
df_covid19_region = get_data(scope)

#print(df_covid19_es.head())
#print(df_covid19_region.head())
#print(df_regions)
#%% Calculation of new indexes and new columns
df_covid19_region["Date_D"] = pd.to_datetime(df_covid19_region["Date"],format="%Y/%m/%d")
df_covid19_region["Date"] = df_covid19_region["Date_D"] 
df_covid19_region.drop(['Date_D'],axis=1,inplace=True)
df_covid19_region = df_covid19_region.sort_values(by=[region_title, "Date"])
#%% create a new index based from day after 5 deaths
df_covid19_region["days_after_5_deaths"] = (
    df_covid19_region[df_covid19_region.Deaths > 5]
    .groupby(by=region_title)["Deaths"]
    .rank(method="first", ascending=True)
)
#%% create a new index based from day after 50 confirmed
df_covid19_region["days_after_50_confirmed"] = (
    df_covid19_region[df_covid19_region.Confirmed > 50]
    .groupby(region_title)["Confirmed"]
    .rank(method="first", ascending=True)
)

#maybe remove this line. Could be useful if I want to show for each country where they start to had COVID issues
df_covid19_region = df_covid19_region.fillna(value=0)
#%% create necessary variables

df_covid19_region["New_Deaths"] = df_covid19_region.groupby(region_title)["Deaths"].diff()
df_covid19_region["New_Cases_AVG"] = df_covid19_region.groupby(region_title)['New_cases'].transform(lambda x: x.rolling(5, 1).mean())
df_covid19_region["New_Deaths_AVG"] = df_covid19_region.groupby(region_title)['New_Deaths'].transform(lambda x: x.rolling(5, 1).mean())

df_covid19_region["dead_ratio"] = df_covid19_region["Deaths"]/df_covid19_region["Population"]*100000
df_covid19_region["cases_ratio"] = df_covid19_region["Confirmed"]/df_covid19_region["Population"]*100000
df_covid19_region["new_cases_ratio"] = df_covid19_region["New_cases"]/df_covid19_region["Population"]*100000
df_covid19_region["new_death_ratio"] = df_covid19_region["New_Deaths"]/df_covid19_region["Population"]*100000


df_covid19_region["Active Cases"] = df_covid19_region["Confirmed"]-df_covid19_region["Deaths"]-df_covid19_region["Recovered"] 


x_date_var = "Date"


#%% Streamlit inputs %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
################################################################################################
viz_option = st.sidebar.selectbox("Visualisation: ", ("-","cumulative", "day delta"))

regions = list(df_covid19_region[region_title].unique())
if scope=="World":
    df_max_conf = (df_covid19_region[[region_title,"Confirmed"]]
    .groupby(region_title).max()
    .sort_values(by="Confirmed",ascending=False)
    )
    regions_def = (df_max_conf.index[:12].to_list())
    if "Korea, South" not in regions_def:
        regions_def[-1] = "Korea, South"
    del df_max_conf
    regions_def.sort()
else:
    regions_remove = ['Ceuta','Melilla']
    regions_def = regions.copy()
    for ccaa in regions_remove:
        regions_def.remove(ccaa)
# Quizás para ESpaña quitar Ceuta y Melilla

multiselection = st.sidebar.multiselect(
    "Choose the regions:", regions, default=regions_def
)


#%% get df_covid19_region based on region in multiselection
# unit_testing variables
# multiselection = regions
# viz_option = "graph"
# scale = "linear"

# Copy of all regions for the map plot
data_all = df_covid19_region[["Country","Lat","Long_","Confirmed","Date"]].copy()
data_all["Date_N"] = (
    data_all.groupby(by=region_title)["Date"]
    .rank(method="first", ascending=True)
)


df_covid19_region = df_covid19_region[
    df_covid19_region[region_title].isin(multiselection)
].sort_values(by=[region_title, x_date_var], ascending=[True, False])

df_covid19_region["Confirmed_label"] = "Active"
df_covid19_region["Active_cases_label"] = "Active cases"
# intentar pintarlo awquí fuera
# comparar mis datos con los originales
# ver si el script original funciona en interactivo

# c_deaths = (
#     alt.Chart(df_covid19_es).
#     mark_line(point=True).
#     encode(
#             x="days_after_5_deaths",
#             y="muertes",
#         ).interactive()
# )

st.sidebar.info(
    "Thanks to Tlse Data Engineering for the [original project](https://github.com/TlseDataEngineering/data-app-covid19)."
)

text_4_regions = """👈 You can remove/add regions from the left and graphs are updated automatically."""

# source = vg_data.unemployment_across_industries.url

# selection = alt.selection(type="multi",fields=['series'], bind="legend",on="click")

# test_c = alt.Chart(source).mark_area().encode(
#     alt.X('yearmonth(date):T', axis=alt.Axis(domain=False, format='%Y', tickSize=0)),
#     alt.Y('sum(count):Q', stack='center', axis=None),
#     alt.Color('series:N', scale=alt.Scale(scheme='category20b')),
#     opacity=alt.condition(selection, alt.value(1), alt.value(0.2))
# ).add_selection(
#     selection
# )
# st.altair_chart(test_c, use_container_width=True)

#single_nearest = alt.selection_single(on='mouseover', nearest=True,empty='none')
#single_nearest = alt.selection_multi(nearest=True)#,fields=[region_title],bind='legend'
#single_nearest = alt.selection_multi(fields=[region_title],bind='legend',on="click")
single_nearest = alt.selection(type='multi',fields=[region_title],nearest=True)
#single_nearest_mo = alt.selection_multi(on='mouseover',nearest=True)#,fields=[region_title],bind='legend'
# POssible fix to complicated selection: https://altair-viz.github.io/gallery/multiline_highlight.html

base = (
    alt.Chart(df_covid19_region)    
    .encode(
        # color=alt.condition(
        #     single_nearest,
        #     alt.Color(region_title+':N", scale=alt.Scale(scheme="category20b")), 
        #     alt.value('lightgray')),
        #color=alt.Color(region_title+':N", scale=alt.Scale(scheme="category20b")),             
        color=alt.condition(
            #datum.CCAA==col_name_global,
            datum[region_title]==col_name_global,
            alt.value('black'),
            alt.Color(region_title+":N", scale=alt.Scale(scheme="category20"))),
        # opacity = alt.condition(single_nearest, alt.value(1), alt.value(0.2)),
        # size = alt.condition(~single_nearest, alt.value(1.5), alt.value(2.5)),
    )
    #.interactive()
)

theseractus_points = (base.mark_circle().encode(
        opacity=alt.value(0)
    ).add_selection(
        single_nearest
    ).properties(
        width=600
    )
    )

lines = base.mark_line().encode(
    opacity = alt.condition(single_nearest, alt.value(1), alt.value(0.2)),
    size = alt.condition(~single_nearest, alt.value(1.5), alt.value(2.5)),
    #tooltip=[x,y,region_title]
)


Line_Base_Chart = theseractus_points + lines

#%%
if viz_option == "-":
    st.write("""👈 Select an analysis type from the dropdown menu on the left.""")
    

    list_dates = data_all.loc[data_all["Country"]=="China","Date_N"].to_list()
    dates_step = 4
    list_dates = list_dates[::dates_step]
    data_all = data_all[data_all.Date_N.isin(list_dates)]
    #source = alt.topo_feature(vg_data.world_110m.url, 'countries')
    source = alt.topo_feature(world_json,'countries1')

    # Igual quitar los países que no tengan apenas nada

    #background_C = 
    slider = alt.binding_range(min=list_dates[0], max=list_dates[-1], step=dates_step, name='Days since 22/01/2020:')
    selector = alt.selection_single(name="Date_N", fields=['Date_N'],
                            bind=slider,init={'Date_N':1})

    map_holder = st.altair_chart(source)
    color = 'crimson'
    points = (
        alt.Chart(data_all).mark_circle(filled=True,fillOpacity=0.4,width=1.25,stroke=color)
        .encode(
                longitude='Long_:Q',
                latitude='Lat:Q',
                size=alt.Size(
                    'Confirmed:Q', 
                    title='Confirmed cases',
                    scale=alt.Scale(domain=[0,100000]),
                    legend=alt.Legend(orient="top")),
                color=alt.value(color),                
                tooltip=['Country:N','Confirmed:Q'])
        .transform_filter(selector)
        .add_selection(
        selector))

    selector.i

    # Layering and configuring the components
    map_chart = alt.layer(           
        alt.Chart(source).mark_geoshape(fill='lightgrey', stroke='black'),
        points,
    ).project(
        'naturalEarth1'
    ).properties(width=750, height=500).configure_view(stroke=None)

    map_holder.altair_chart(map_chart)   #

    # st.altair_chart(map_chart)#, use_container_width=True)

    # st.write("Slider tests")
    # dates_slider = st.slider("Date", int(list_dates[0]), int(list_dates[-1]), 1,dates_step)
    # st.write("Slider says",dates_slider)
##########################################################################################################
##########################################################################################################
elif viz_option == "cumulative":
    st.write(text_4_regions)
    if st.checkbox("Relative x-axis"):
        x_var = ["days_after_50_confirmed","days_after_5_deaths"]
    else:
        x_var = [x_date_var,x_date_var]
    
    if st.checkbox("Numbers relative to population"):
        y_var = ["cases_ratio","dead_ratio"]
        st.info("""Values are relative to 100k people""")
    else:
        y_var = ["Confirmed","Deaths"]        
    
    if st.checkbox("Log Scale"):
        max_log_cases = [truncate_10(df_covid19_region[y_var[0]].max(),"up"),
         truncate_10(df_covid19_region[y_var[1]].max(),"up")]
        min_log_cases = (
            [truncate_10(
                df_covid19_region[df_covid19_region[y_var[0]]>0][y_var[0]].min(),"down"),
         truncate_10(
                df_covid19_region[df_covid19_region[y_var[1]]>0][y_var[1]].min(),"down")])
        scale_t = "log"
    else:
        scale = alt.Scale(type="linear")
        scale_t = "linear"        

    # make plot on nb of diagnosed by regions    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)
    
    st.write("""You can highlight lines from the graphs below 👇 by holding shift + left click.
    To remove the selection double click anywhere in the graph.""")
    



    c_diagnosed = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[0]),
            alt.Y(y_var[0], scale=scale),       
            tooltip=[x_var[0], y_var[0], region_title],                    
    ))    
 
    # make plot on nb of deces by regions
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    c_deaths = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[1]),
            alt.Y(y_var[1], scale=scale),
            tooltip=[x_var[1], y_var[1], region_title],
        )
    )
    
    full_cumulated = alt.vconcat(c_diagnosed, c_deaths)
    
    st.altair_chart(full_cumulated, use_container_width=True)
    # st.altair_chart(c_diagnosed, use_container_width=True)
    # st.altair_chart(c_deaths, use_container_width=True)
    # st.write("""\n\n""")
    st.markdown("---")

    st.info("""Cumulated distributions of total cases, recovered and fatalities""")
    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)
    if st.checkbox("y axis independent for each region",value=True):
        y_scale_rs = "independent"
    else:
        y_scale_rs = "shared"
        if scale_t == "log":
            scale = alt.Scale(type="log", clamp=True)

    area_st_base = (
        alt.Chart(df_covid19_region)
        .encode(            
            x=x_var[0],
        ).properties(
            height=150,
            width=180,
    )

    )
    area_st_1 = (
        area_st_base.mark_area(opacity=0.5,line=True)
        .encode(
            alt.Y('Confirmed:Q',scale=scale,axis=alt.Axis(title='count')),
            color=alt.value('#1f77b4'),
            opacity=alt.Opacity('Confirmed_label', legend=alt.Legend(title=None))     
            #color=alt.Color('Confirmed:N', scale=alt.Scale(range=['#1f77b4']), legend=alt.Legend(title=None))
        ))
    area_st_2 = (
        area_st_base.mark_area(opacity=0.85,line=True)
        .transform_fold(['Deaths','Recovered'])   
        .encode(
            alt.Y('value:Q',stack=True,scale=scale,axis=alt.Axis(title='count')),
            color=alt.Color('key:N',
                    scale=alt.Scale(
                        range=['#e41a1c','#71f594']),
                    legend=alt.Legend(title=None)),#ff7f0e,#71f594
            order = "key:N",     
        ))    
    line_st_3 =(
        area_st_base.mark_line()
        .encode(
            alt.Y("Active Cases:Q",scale=scale,axis=alt.Axis(title='count')),
            color=alt.value('black'),
            size = alt.value(2),
            shape=alt.Shape('Active_cases_label', legend=alt.Legend(title=None))
        )
    )
    c_area_st = alt.layer(    
    area_st_1,
    area_st_2,
    line_st_3,
    ).facet(    
        facet=region_title+':N',
        columns=3
    ).resolve_scale(y=y_scale_rs)     

    st.altair_chart(c_area_st, use_container_width=True)

##########################################################################################################
##########################################################################################################

elif viz_option=="day delta":
    st.write(text_4_regions)
    if st.checkbox("Relative x-axis"):
        x_var = ["days_after_50_confirmed","days_after_5_deaths"]
        x_hist = alt.X(x_var[0]+':Q',band=0,
                    axis=alt.Axis(title='Days'))
    else:
        x_var = [x_date_var,x_date_var]
        x_hist = alt.X(x_var[0],type="temporal",timeUnit="yearmonthdate",
                    axis=alt.Axis(format="%b-%d",title='date'))
    
    if st.checkbox("Numbers relative to population"):
        y_var = ["new_cases_ratio","new_deaths_ratio"]
        st.info("""Values are relative to 100k people""")
    else:
        y_var = ["New_cases","New_Deaths"]   

    if st.checkbox("Perform rolling average (5 days period)",value=True):
        y_var = ["New_Cases_AVG","New_Deaths_AVG"]        
    else:
        y_var = ["New_cases","New_Deaths"]   
    
    if st.checkbox("Log Scale"):
        max_log_cases = [truncate_10(df_covid19_region[y_var[0]].max(),"up"),
         truncate_10(df_covid19_region[y_var[1]].max(),"up")]
        min_log_cases = (
            [truncate_10(
                df_covid19_region[df_covid19_region[y_var[0]]>0][y_var[0]].min(),"down"),
         truncate_10(
                df_covid19_region[df_covid19_region[y_var[1]]>0][y_var[1]].min(),"down")])
        scale_t = "log"
    else:
        scale = alt.Scale(type="linear")
        scale_t = "linear" 

    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)

    c_diagnosed_new = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[0]),
            alt.Y(y_var[0], scale=scale),       
            tooltip=[x_var[0], y_var[0], region_title],                    
    ))    
    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    c_deaths_new = (
        Line_Base_Chart
        .encode(
            alt.X(x_var[1]),
            alt.Y(y_var[1], scale=scale),
            tooltip=[x_var[1], y_var[1], region_title],
        )
    )
    
    full_cumulated = alt.vconcat(c_diagnosed_new, c_deaths_new)

    c_heatmap_confirmed = (
        alt.Chart(df_covid19_region)
        .mark_rect()
        .encode(
            alt.X(x_var[0]),
            alt.Y(region_title+":N"),
            alt.Color(y_var[0]+":Q", scale=alt.Scale(scheme="yelloworangered")), #iridis
            tooltip=[x_var[0], region_title, y_var[0]],
        )
        .transform_filter((datum.New_cases >= 0))
        .interactive()
    )
    st.altair_chart(full_cumulated, use_container_width=True)
    st.altair_chart(c_heatmap_confirmed, use_container_width=True)
    st.write("""\n\n""")
    if st.checkbox("y axis independent for each region"):
        y_scale_rs = "independent"
    else:
        y_scale_rs = "shared"
    c_histog_new = (
        alt.Chart(df_covid19_region)
        .mark_bar()#width)
        .encode(            
            x_hist,
            alt.Y(y_var[0]+":Q"),            
            tooltip=[x_var[0], y_var[0]],
        )
        .properties(
            height=180,
            width=180,
            )
        .facet(
            facet=region_title+':N',
            columns=3,
        ).resolve_scale(y=y_scale_rs)
        .interactive()
    )
    
    
    st.altair_chart(c_histog_new, use_container_width=True)

    # st.info("""Aquí me gustaría probar los ridgelines. Quizás lo que más me guste es lollypop""")

elif viz_option=="histo":
    st.info("""En alguna parte podría pintar unas barras rellenas. Total de casos rellenos con el 
    porcentaje de curados, hospitalizados, UCI, muertos. O barras superpuestas unas sobre otras con
    transparencia""")

st.info(
    """ by: [R. Jimenez Sanchez](https://www.linkedin.com/in/robertojimenezsanchez/) | source: [GitHub](https://www.github.com)
        | data source: [victorvicpal/COVID19_es (GitHub)](https://github.com/victorvicpal/COVID19_es/blob/master/data/final_data/dataCOVID19_es.csv). """
)




# %%
