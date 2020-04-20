#%%
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
import time

from math import ceil, floor, log10
#from vega_datasets import data as vg_data

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
url_ccaa_coords = "/home/roberto/Documents/python/scripts/covid/data/CCAA_coords.csv"

json_root = "https://raw.githubusercontent.com/deldersveld/topojson/master/"
world_json = json_root+"world-countries-sans-antarctica.json"
spain_json = json_root+"countries/spain/spain-comunidad-with-canary-islands.json"


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
        df_coords = pd.read_csv(url_ccaa_coords,encoding='ISO-8859-14')
        data = data.merge(df_coords,how="left")
        #data['Lat'] = data['Long_'] = np.nan
    
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
# Patch :  remove eventually

y_map_var = "Active Cases"
data_all = (
    df_covid19_region.loc[df_covid19_region[region_title]!=col_name_global,
            [region_title,"Lat","Long_",y_map_var,"Date"]].copy())
data_all["Date_N"] = (
    data_all.groupby(by=region_title)["Date"]
    .rank(method="first", ascending=True)
)


df_covid19_region = df_covid19_region[
    df_covid19_region[region_title].isin(multiselection)
].sort_values(by=[region_title, x_date_var], ascending=[True, False])

df_covid19_region["Confirmed_label"] = "Active"
df_covid19_region["Active_cases_label"] = "Active cases"


st.sidebar.info(
    "Thanks to Tlse Data Engineering for the [original project](https://github.com/TlseDataEngineering/data-app-covid19)."
)

text_4_regions = """👈 You can remove/add regions from the left and graphs are updated automatically."""

single_nearest = alt.selection(
    type='multi',fields=[region_title],nearest=True,
    #init={region_title:'Spain'}
)

def line_base_chart(x_var,y_var,scale_var):
    
    
    base = (
        alt.Chart(df_covid19_region)    
        .encode(            
            color=alt.condition(                
                datum[region_title]==col_name_global,
                alt.value('black'),
                alt.Color(region_title+":N", scale=alt.Scale(scheme="category20"))),
        #     # opacity = alt.condition(single_nearest, alt.value(1), alt.value(0.2)),
        #     # size = alt.condition(~single_nearest, alt.value(1.5), alt.value(2.5)),
        )
        #.interactive()
    )

    min_day = df_covid19_region[x_var].min()
    max_day = df_covid19_region[x_var].max()
    if x_var=='Date':
        max_disp = (max_day+0.15*(max_day-min_day)).round('d')
        domain = [min_day.isoformat(), max_disp.isoformat()]
    else:
        max_disp = max_day+0.15*(max_day-min_day)
        domain = [min_day, max_disp]

    theseractus_points = (base.mark_circle().encode(            
            alt.X(x_var,scale=alt.Scale(domain = domain)),
            alt.Y(y_var, scale=scale_var),       
            # tooltip=[x_var, y_var, region_title],
            opacity=alt.value(0),
        ).add_selection(
            single_nearest
        ).properties(
            width=600
        )
        )

    opacity_common = alt.condition(single_nearest, alt.value(1), alt.value(0.2))

    point_end = base.mark_point(filled=True).encode(
        x=alt.X('max('+x_var+')',axis=alt.Axis(title=x_var)),
        y=alt.Y(y_var, aggregate={'argmax': x_var},axis=alt.Axis(title=y_var)),
        opacity = opacity_common,
        #shape=region_title+":N",
        size = alt.value(60),
        # color = alt.Color(region_title+":N", scale=alt.Scale(scheme="category20")),
        # color=alt.condition(
        #         #datum.CCAA==col_name_global,
        #         datum[region_title]==col_name_global,
        #         alt.value('black'),
        #         alt.Color(region_title+":N", scale=alt.Scale(scheme="category20"))),
        
    )

    lines = base.mark_line().encode(
        alt.X(x_var),
        alt.Y(y_var, scale=scale_var),       
        tooltip=[x_var, y_var, region_title],
        opacity = opacity_common,
        size = alt.condition(~single_nearest, alt.value(2), alt.value(3)),
        # color=alt.condition(                
        #         datum[region_title]==col_name_global,
        #         alt.value('black'),
        #         alt.Color(region_title+":N", scale=alt.Scale(scheme="category20"),legend=None)),       
    )#.add_selection(single_nearest).properties(width=600)

    

    text_end = (base.mark_text(
                    align='left', baseline='middle', dx=4
        ).encode(
            x=alt.X('max('+x_var+')',axis=alt.Axis(title=x_var)),
            y=alt.Y(y_var, aggregate={'argmax': x_var},axis=alt.Axis(title=y_var)),
            text=alt.Text(region_title+":N"),
            #color=alt.value('black'),
            opacity = opacity_common,
            # color=alt.condition(                
            #     datum[region_title]==col_name_global,
            #     alt.value('black'),
            #     alt.Color(region_title+":N", scale=alt.Scale(scheme="category20"),legend=None)),
    ))

    return alt.layer(
        theseractus_points,
        point_end,
        lines,
        text_end)

#%%
if viz_option == "-":
    st.write("""👈 Select an analysis type from the dropdown menu on the left.""")

    

    if scope == "World":   
        source = alt.topo_feature(world_json,'countries1')
        scale_map=alt.Scale(domain=[0,100000])
    else:
        st.write("Map for Spain is under construction")
        source = alt.topo_feature(spain_json,'ESP_adm1')
        scale_map=alt.Scale(domain=[0,10000])

    list_dates = data_all.loc[data_all[region_title]==multiselection[0],"Date_N"].to_list()
    # Calcularlo automáticamente
    dates_step = ceil(len(regions)*len(list_dates)/5000)
    list_dates = list_dates[::dates_step]
    data_all = data_all[data_all.Date_N.isin(list_dates)]
    #source = alt.topo_feature(vg_data.world_110m.url, 'countries')
    
    # for spain it is NAME_1

    # Igual quitar los países que no tengan apenas nada en la última fecha

    #background_C = 
    slider = alt.binding_range(min=list_dates[0], max=list_dates[-1], step=dates_step, name='Days since 22/01/2020:')
    selector = alt.selection_single(name="Date_N", fields=['Date_N'],
                            bind=slider,init={'Date_N':1})

    map_holder = st.altair_chart(source)
    color = 'crimson'
    points = (
        alt.Chart(data_all).mark_point(
            filled=True,fillOpacity=0.4,
            strokeWidth=1,strokeOpacity=1,stroke=color)
        .encode(
                longitude='Long_:Q',
                latitude='Lat:Q',
                size=alt.Size(
                    y_map_var+':Q', 
                    title='Active cases',
                    scale=scale_map,
                    legend=alt.Legend(orient="top"),
                    ),                
                color=alt.value(color),                
                tooltip=[region_title+':N',y_map_var+':Q'])
        .transform_filter(selector)
        .add_selection(
        selector))

    text_map = (
        alt.Chart(data_all).mark_text()
        .encode(
            longitude=alt.value(-145.1),
            latitude=alt.value(-41.4),
            text='Date',
            size=alt.value(20)
        ).transform_filter(selector)
    )

    # Layering and configuring the components
    map_chart = alt.layer(           
        alt.Chart(source).mark_geoshape(fill='lightgrey', stroke='black'),
        points,
        text_map,
    ).project(
        'naturalEarth1'
    ).properties(width=750, height=500).configure_view(stroke=None)

    map_holder.altair_chart(map_chart)   #

    # else:
        
    #     map_chart = (           
    #         alt.Chart(source).mark_geoshape(fill='lightgrey', stroke='black')
    #         .project(
    #             'naturalEarth1'
    #         ).properties(width=750, height=500).configure_view(stroke=None)
    #     )
        
    #     st.altair_chart(map_chart)
##########################################################################################################
##########################################################################################################
elif viz_option == "cumulative":
    st.write(text_4_regions)
    options_for_x = ("Date","Days since 50 cases", "Days since 5 deaths")
    x_option = st.selectbox("x-axis: ", options_for_x,index=1)
    
    if x_option == options_for_x[1]:
        x_var = "days_after_50_confirmed"
    elif x_option == options_for_x[2]:
        x_var = "days_after_5_deaths"
    else:
        x_var = x_date_var
    
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
    
   

    c_diagnosed = line_base_chart(x_var,y_var[0],scale)
 
    # make plot on nb of deces by regions
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    
    c_deaths = line_base_chart(x_var,y_var[1],scale)
    
    full_cumulated = alt.vconcat(c_diagnosed, c_deaths)
    
    st.altair_chart(full_cumulated, use_container_width=True)
    # st.altair_chart(c_diagnosed, use_container_width=True)
    # st.altair_chart(c_deaths, use_container_width=True)
    # st.write("""\n\n""")
    st.markdown("---")

    st.write("""The stacked areas below show the cumulated distributions of active cases, 
    recovered and death, which gives the total COVID-19 cases per """+region_title+""". 
    Additionally, the active cases are plotted in a separated line""")
    
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
            x=x_var,
        ).properties(
            height=150,
            width=180,
    )

    )
    area_st_1 = (
        area_st_base.mark_area(opacity=0.5,line=True)
        .encode(
            alt.Y('Confirmed:Q',axis=alt.Axis(title='count')),
            color=alt.value('#1f77b4'),
            opacity=alt.Opacity('Confirmed_label', legend=alt.Legend(title=None))     
            #color=alt.Color('Confirmed:N', scale=alt.Scale(range=['#1f77b4']), legend=alt.Legend(title=None))
        ))
    area_st_2 = (
        area_st_base.mark_area(opacity=0.85,line=True)
        .transform_fold(['Deaths','Recovered'])   
        .encode(
            alt.Y('value:Q',stack=True,axis=alt.Axis(title='count')),
            color=alt.Color('key:N',
                    scale=alt.Scale(
                        range=['#e41a1c','#71f594']),
                    legend=alt.Legend(title=None)),#ff7f0e,#71f594
            order = "key:N",     
        ))    
    line_st_3 =(
        area_st_base.mark_line()
        .encode(
            alt.Y("Active Cases:Q",axis=alt.Axis(title='count')),
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
    
    
    c_diagnosed_new = line_base_chart(x_var[0],y_var[0],scale)
    
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    c_deaths_new = line_base_chart(x_var[1],y_var[1],scale)
    
    full_cumulated = alt.vconcat(c_diagnosed_new, c_deaths_new)


    st.altair_chart(full_cumulated, use_container_width=True)

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


st.info(
    """ by: [R. Jimenez Sanchez](https://www.linkedin.com/in/robertojimenezsanchez/) | Code: [GitHub](https://www.github.com)
        | data source: [victorvicpal/COVID19_es (GitHub)](https://github.com/victorvicpal/COVID19_es/blob/master/data/final_data/dataCOVID19_es.csv). """
)




# %%
