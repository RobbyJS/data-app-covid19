#%%
import pandas as pd
import streamlit as st
from numpy import where, nan
import common_vars as comv
from pathlib import Path

#%%
## URLs with all necessary data
# World data URLs:
url_intern_root = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/"
time_series_path = "csse_covid_19_time_series/" 
url_inter_conf = url_intern_root+time_series_path+"time_series_covid19_confirmed_global.csv"
url_inter_death = url_intern_root+time_series_path+"time_series_covid19_deaths_global.csv"
url_inter_recov = url_intern_root+time_series_path+"time_series_covid19_recovered_global.csv"
url_cov_country_codes = url_intern_root+"UID_ISO_FIPS_LookUp_Table.csv"

# Spain data URLs:
url_spain_root = "https://raw.githubusercontent.com/victorvicpal/COVID19_es/master/data/"
URL_OPENCOVID19 = url_spain_root+"final_data/dataCOVID19_es.csv"
url_pop_ccaa = url_spain_root+"info_data/Poblaci%C3%B3nCCAA.csv"

url_ccaa_coords = "https://raw.githubusercontent.com/RobbyJS/data-app-covid19/master/data/CCAA_coords.csv"
url_ccaa_mapping = "https://raw.githubusercontent.com/RobbyJS/data-app-covid19/master/data/CCAA_mapping.csv"

url_spain_root = "https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/"
url_spain_conf = url_spain_root+"ccaa_covid19_casos_long.csv"
url_spain_death = url_spain_root+"ccaa_covid19_fallecidos_long.csv"
url_spain_recov = url_spain_root+"ccaa_covid19_altas_long.csv"

#%%
def intern_data_ops(df,value_df):
    """Set of operations that are necessary on the three files containing the international data:
            - Remove unnecessary columns
            - Fold columns into rows for plotting with Altair"""
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
    return df
#%%
def spain_data_ops(df,col_name):
    df.drop(["cod_ine"],axis=1,inplace=True)
    df.rename(columns={'total':col_name,'fecha':'Date'},inplace=True)
    return df
#%%
def compute_days_count(df,region_title,y_col,thresh,new_y_col):
    # st.write("""I'm in compute days count""")
    df2 = (
        df.loc[df[y_col] > thresh,[region_title,'Date']]
        .groupby(by=region_title,as_index=False).min()
    )    
    df2.rename(columns={'Date':new_y_col},inplace=True)
    
    df = df.merge(df2,on=[region_title],how="inner")
    df[new_y_col] = (df['Date']-df[new_y_col]).astype('timedelta64[D]')
    
    df.loc[df[new_y_col]<0,new_y_col] = nan
    return df


def find_outliers(df,region_title,y_col,thresh):
    # st.write("""I'm in compute days count""")
    df["perc_var"] = df.groupby(by=region_title)[y_col].pct_change() #periods=1, fill_method=None
    mask_out = df["perc_var"]<-1*thresh
    df.loc[mask_out,y_col] = nan

    return df[y_col]

@st.cache
def get_data(which_data='World') :
    """
    1 - Get data from open repositories
    2 - Apply transformations to obtain dataframes with the same columns both for Spain and World data
    3 - Returns df_covid19_region (columns = [region_title, 'Date', 'Confirmed', 'Deaths', 'Recovered', 
                                        'Population','New_cases','Lat','Long_']) 
    """
    

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
        mask_countries = where(df_codes[region_title] == df_codes['Combined_Key']
                            , True, False)
        df_codes = df_codes[mask_countries]
        # And we add the population column to COVID data by merge operation
        data = data.merge(df_codes[[region_title,'Population','Lat', 'Long_']],how="left")
        # I need a column with the new cases
            # compute delta_cas_confirmes by making the diff between rows on cas_confirmes grouped by region
        data["New_Cases"] = data.groupby(region_title)["Confirmed"].diff()
        # Coming out of this condition I have the data df which contains: 
        # Index(['Country', 'Date', 'Confirmed', 'Deaths', 'Recovered', 'Population','New_cases','Lat','Long_'], dtype='object')
        # I need the same for Spain data. Except maybe for 'Country' == "CCAA"


    else:
        region_title = "CCAA"
        # 1 - Get COVID data
        col_names = ["CCAA","Date"]
        data = spain_data_ops(pd.read_csv(url_spain_conf),"Confirmed")
        data = data.merge(
            spain_data_ops(pd.read_csv(url_spain_death),"Deaths"),on=col_names,how='left')
        data = data.merge(
            spain_data_ops(pd.read_csv(url_spain_recov),"Recovered"),on=col_names,how='left')
 
        df_mapping = pd.read_csv(url_ccaa_mapping,encoding='ISO-8859-14')
        df_mapping.set_index(keys="old",inplace=True)   
        df_mapping2 = pd.Series(df_mapping["new"])     
        dict_mapping = df_mapping2.to_dict()
        del df_mapping, df_mapping2

        # 2 - Get regions population data
        df_regions = pd.read_csv(url_pop_ccaa)
        df_regions.rename(columns={"Población":"Population"},
                    inplace=True)
        # Replace CCAA names to match with the ones with COVID data (set first column as index)
        df_regions.CCAA.replace(to_replace=dict_mapping,value=None,inplace=True)
        # add population information
        data = data.merge(df_regions,on=region_title,how='inner')

        # 3 - Keep only the necessary columns
        data = data[[region_title, 'Date', 'Confirmed', 'Deaths', 'Recovered', 'Population']]#,'New_Cases']]
        # data.drop(['IA','Densidad'],axis=1,inplace=True)

        # 4 - Calculate the data for the whole country 
        col_idx = list(range(0,data.shape[1]))
        df_covid19_es = data.iloc[:,col_idx].groupby(['Date'],as_index=False).sum()        
        df_covid19_es[region_title] = comv.col_name_global
        df_covid19_es = df_covid19_es.fillna(value=0)

        data = data.append(df_covid19_es,ignore_index=True)
        del df_covid19_es

        # 5 Add region coordinates for map plot
        df_coords = pd.read_csv(url_ccaa_coords,encoding='ISO-8859-14')
        df_coords.CCAA.replace(to_replace=dict_mapping,value=None,inplace=True)
        data = data.merge(df_coords,how="left")
        
    
    #----------------------------------------------------------------------------------------#
    # Data manipulations
    # 0. Interpolate missing data for days in which data is not reported

    # 1. Calculation of new indexes and new columns
    data["Date_D"] = pd.to_datetime(data["Date"],format="%Y/%m/%d")
    data["Date"] = data["Date_D"] 
    data.drop(['Date_D'],axis=1,inplace=True)
    
    # Remove duplicate rows (rows with same date):
    #data = data.groupby([region_title,'Date'],as_index=False).max()

    data = data.sort_values(by=[region_title, "Date"],ignore_index=True)

    #st.write(data)

    # 2. create a new indexes based from days after 5 deaths & 50 confirmed

    # The problem of operating this way is that the data is reordered. To be more efficient...
    # Maybe I can do with concat keeping indexes: https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html

    # data["days_after_5_deaths"] = compute_days_count(data[[region_title,"Date","Deaths"]],region_title,"Deaths",5)
    # data["days_after_50_confirmed"] = compute_days_count(data[[region_title,"Date","Confirmed"]],region_title,"Confirmed",50)

    data = compute_days_count(data,region_title,"Deaths",5,"days_after_5_deaths")
    data = compute_days_count(data,region_title,"Confirmed",50,"days_after_50_confirmed")

    # data["days_after_5_deaths"] = (
    #     data[data.Deaths > 5]
    #     .groupby(by=region_title)["Deaths"]
    #     .rank(method="first", ascending=True)
    # )
    # 3. create a new index based from day after 50 confirmed
    # pensar si lo hago de otra manera para los días en que no hay datos no encontrarme con NaN
    # data["days_after_50_confirmed"] = (
    #     data[data.Confirmed > 50]
    #     .groupby(region_title)["Confirmed"]
    #     .rank(method="first", ascending=True)
    # )

    #maybe remove this line. Could be useful if I want to show for each country where they start to had COVID issues
    # Interpolate confirmed, death & recovered count when data streaming has started and value is nan:
    # data[['Confirmed','Deaths','Recovered']] = (data[['Confirmed','Deaths','Recovered']]
    #                                             .interpolate(method='spline', order=4,axis=0, limit=None, inplace=False))

    #st.write("Data before outlier detection")
    #st.write(data)
    # Una de las operaciones me está quitando Ceuta    
    # data["Confirmed"] = find_outliers(data[[region_title,"Confirmed"]],region_title,"Confirmed",0.75)
    # data["Deaths"] = find_outliers(data[[region_title,"Deaths"]],region_title,"Deaths",0.75)
    # data["Recovered"] = find_outliers(data[[region_title,"Recovered"]],region_title,"Recovered",0.75)
    
    #st.write("Data before interpolationn")
    #st.write(data)
    # data['Confirmed'] = (data['Confirmed']
    #                                     .interpolate(method='spline', order=4, limit=2, inplace=False,limit_direction='backward'))

    # (data['Deaths'].interpolate(method='spline', order=4, limit=2, inplace=True,limit_direction='backward'))
    # 1. Find data that makes no sense (isolated points without data or with huge change in data and replace by NaN)

    data["Confirmed"] = data.groupby(region_title)['Confirmed'].transform(
         lambda x: x.interpolate(method='linear', axis=0, limit=2, inplace=False,limit_direction='forward'))

    data["Deaths"] = data.groupby(region_title)['Deaths'].transform(
         lambda x: x.interpolate(method='linear', axis=0, limit=2, inplace=False,limit_direction='forward'))

    data["Recovered"] = data.groupby(region_title)['Recovered'].transform(
         lambda x: x.interpolate(method='linear', axis=0, limit=2, inplace=False,limit_direction='forward'))         


    #st.write("Data after interpolation")
    #st.write(data)


    data = data.fillna(value=0)
    #%% create necessary variables

    data["New_Cases"] = data.groupby(region_title)["Confirmed"].diff()
    data["New_Deaths"] = data.groupby(region_title)["Deaths"].diff()
    data["New_Recovered"] = data.groupby(region_title)["Recovered"].diff()

    data["New_Cases_AVG"] = data.groupby(region_title)['New_Cases'].transform(lambda x: x.rolling(5, 1).mean())
    data["New_Deaths_AVG"] = data.groupby(region_title)['New_Deaths'].transform(lambda x: x.rolling(5, 1).mean())
    data["New_Recovered_AVG"] = data.groupby(region_title)['New_Recovered'].transform(lambda x: x.rolling(5, 1).mean())

    data["dead_ratio"] = data["Deaths"]/data["Population"]*100000
    data["cases_ratio"] = data["Confirmed"]/data["Population"]*100000
    # data["new_cases_ratio"] = data["New_cases"]/data["Population"]*100000
    # data["new_death_ratio"] = data["New_Deaths"]/data["Population"]*100000


    data["Active Cases"] = data["Confirmed"]-data["Deaths"]-data["Recovered"] 
    
    # Regions to work with and default starting regions
    regions = list(data[region_title].unique())
    # st.write(regions)
    if which_data=="World":
        df_max_conf = (data[[region_title,"Confirmed"]]
        .groupby(region_title).max()
        .sort_values(by="Confirmed",ascending=False)
        )
        regions_def = (df_max_conf.index[:12].to_list())
        if "Korea, South" not in regions_def:
            regions_def[-1] = "Korea, South"
        del df_max_conf
        regions_def.sort()
    else:
        regions_remove = ['Ceuta','Melilla',comv.col_name_global]
        regions_def = regions.copy()
        for ccaa in regions_remove:
            # st.write("Removing "+ccaa)
            try:
                regions_def.remove(ccaa)   
            except ValueError:
                pass  # do nothing!
            
            
    
    return data, region_title,regions, regions_def


def read_markdown_file(markdown_file):
    return Path(markdown_file).read_text()