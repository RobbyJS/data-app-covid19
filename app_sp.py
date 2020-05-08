#%%
from math import ceil, floor, log10
import time

import streamlit as st
import altair as alt
from altair import datum

import helpers as hp
import my_alt_graphs as myag 
import common_vars as comv

#%% Truncate function
def truncate_10(n,up_down):
    temp = floor(log10(n))
    if up_down == "up":
        round_op = lambda x: ceil(x)
    else:
        round_op = lambda x: floor(x)

    return float(round_op(n/10**temp)*(10**temp))


#%%

scope = st.sidebar.selectbox("Scope of Analysis:", ("World","Spain"))
#scope = "Spain"

with st.spinner('Data is being loaded...'):
    time.sleep(3)
    df_covid19_region,region_title,regions,regions_def = hp.get_data(scope)
    

#%% Streamlit inputs %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
################################################################################################
st.title("DataViz App Covid-19 🦠")
st.header("Analysis of "+scope+" data")
viz_option = st.sidebar.selectbox("Visualisation: ", ("Map","cumulative", "day delta"))


multiselection = st.sidebar.multiselect(
    "Choose the regions:", regions, default=regions_def
)


y_map_var = "Active Cases"

data_all = (
    df_covid19_region.loc[df_covid19_region[region_title]!=comv.col_name_global,
            [region_title,"Lat","Long_",y_map_var,"Date"]].copy())
data_all["Date_N"] = (
    data_all.groupby(by=region_title)["Date"]
    .rank(method="first", ascending=True)
)


df_covid19_region = df_covid19_region[
    df_covid19_region[region_title].isin(multiselection)
].sort_values(by=[region_title, comv.x_date_var], ascending=[True, False])

df_covid19_region["Confirmed_label"] = "Active"
df_covid19_region["Active_cases_label"] = "Active cases"


st.sidebar.info(
    "Thanks to Tlse Data Engineering for the [original project](https://github.com/TlseDataEngineering/data-app-covid19)."
)

single_nearest = alt.selection(
    type='multi',fields=[region_title],nearest=True)

#%%
if viz_option == "Map":
    st.write("""👈 Select the scope of the analysis from the dropdown menu on the left.
    Choose also the visualisation type.""")

    st.subheader("Map plot")

    map_chart = myag.map_chart_f(scope,data_all,y_map_var,region_title,multiselection,regions)
    st.altair_chart(map_chart)   


#--------------------------------------------------------------------------------------------------------#

elif viz_option == "cumulative":
    st.write(comv.text_4_regions)
    
    #st.write(df_covid19_region)

    x_option = st.selectbox("x-axis: ", comv.options_for_x,index=1)   

    
    if st.checkbox("Numbers relative to population"):
        y_var = ["cases_ratio","dead_ratio"]
        st.write("""Values are relative to 100k people per region""")
    else:
        y_var = ["Confirmed","Deaths"]        
    
    if st.checkbox("Log Scale"):
        max_log_cases = [truncate_10(df_covid19_region[y_var[0]].max(),"up"),
         truncate_10(df_covid19_region[y_var[1]].max(),"up")]
        min_log_cases = (
            [truncate_10(
                df_covid19_region[df_covid19_region[y_var[0]]>0][y_var[0]].min(),"up"),
         truncate_10(
                df_covid19_region[df_covid19_region[y_var[1]]>0][y_var[1]].min(),"up")])
        scale_t = "log"
        scale = alt.Scale(type="log", domain=[min_log_cases[0], max_log_cases[0]], clamp=True)
    else:
        scale = alt.Scale(type="linear")
        scale_t = "linear"        

           
    

    if scope =='Spain':
        st.write("""It is possible to add the country total as a line. Select it as `"""+comv.col_name_global+"""`
                        in the regions selection in the left 👈""")

    st.write(comv.text_line_instructions) 
   
    
    c_diagnosed = myag.line_base_chart(
        df_covid19_region,region_title,single_nearest,
        x_option,y_var[0],scale)
 
    # make plot on nb of deces by regions
    if scale_t == "log":
        scale = alt.Scale(type="log", domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    
    c_deaths = myag.line_base_chart(
        df_covid19_region,region_title,single_nearest,
        x_option,y_var[1],scale)
    
    full_cumulated = alt.vconcat(c_diagnosed, c_deaths)
    
    st.altair_chart(full_cumulated, use_container_width=True)

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


    y_var_area = ['Deaths','Recovered','Active Cases']
    order_var = {'Deaths': 0, 'Recovered': 1, 'Active Cases': 2}

    area_st_d_2 = myag.area_chart_f(
        df_covid19_region,region_title,x_option,y_var_area,
        True,True,order_var,"Active Cases")

    st.altair_chart(area_st_d_2, use_container_width=True)

##########################################################################################################
##########################################################################################################

elif viz_option=="day delta":
    st.write(comv.text_4_regions)
    
       
    x_option = st.selectbox("x-axis: ", comv.options_for_x,index=1)  
    
    # y_var = ["New_Cases","New_Deaths"]   
    if st.checkbox("Perform rolling average (5 days period)",value=True):
        y_var = ["New_Cases_AVG","New_Deaths_AVG","New_Recovered_AVG"]        
    else:
        y_var = ["New_Cases","New_Deaths","New_Recovered"] 

    order_list = [0,2,1]
    order_dict = {}
    for i,elem in enumerate(order_list): order_dict[elem] = y_var[i]

    st.write(comv.text_line_instructions) 

    scale = alt.Scale(type="linear")
    c_diagnosed_new = myag.line_base_chart(
        df_covid19_region,region_title,single_nearest,
        x_option,y_var[0],scale)
    
    # if scale_t == "log":
    #     scale = alt.Scale(type="log")#, domain=[min_log_cases[1], max_log_cases[1]], clamp=True)
    
    c_deaths_new = myag.line_base_chart(
        df_covid19_region,region_title,single_nearest,
        x_option,y_var[1],scale)
    
    full_cumulated = alt.vconcat(c_diagnosed_new, c_deaths_new)

    
    st.altair_chart(full_cumulated, use_container_width=True)

    st.write("""\n\n""")
    st.markdown("---")

    #st.write(df_covid19_region)

    solve_y_scale = st.checkbox("y axis independent for each region",value=True)   

    area_st_d = myag.area_chart_f(df_covid19_region,region_title,x_option,y_var,False,solve_y_scale,None)

    st.altair_chart(area_st_d, use_container_width=True)

st.markdown("---")

data_srcs_markdown = hp.read_markdown_file("data_sources.md")
st.markdown(data_srcs_markdown, unsafe_allow_html=True)

st.write("\n\n")
st.info(
    """ by: [R. Jimenez Sanchez](https://www.linkedin.com/in/robertojimenezsanchez/) | Code: [GitHub](https://github.com/RobbyJS/data-app-covid19)"""
)


