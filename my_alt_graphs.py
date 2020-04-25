from math import ceil

import altair as alt
from altair import datum

import common_vars as comv


def set_x_axis(x_option):
    if x_option == comv.options_for_x[1]:
        x_var = "days_after_50_confirmed"
        x_axis = alt.X(x_var+':Q',band=0,
                    axis=alt.Axis(title='Days'))
    elif x_option == comv.options_for_x[2]:
        x_var = "days_after_5_deaths"
        x_axis = alt.X(x_var+':Q',band=0,
                    axis=alt.Axis(title='Days'))
    else:
        x_var = comv.x_date_var
        x_axis = alt.X(x_var,type="temporal",timeUnit="yearmonthdate",
                    axis=alt.Axis(format="%b-%d",title='Date'))
    return x_var, x_axis

def line_base_chart(df_covid19_region,region_title,single_nearest,x_option,y_var,scale_var,col_name_global):
    '''Function for plotting the line graphs in the app. Inputs:
    - x_var: dataframe column to be used for the x-axis
    - y_var: dataframe column to be used for the y-axis
    - scale: altair scale object that indicates if the scale is linear or logarithmic and the domain, 
        in the latter case.
    The output is a graph based on Altair Charts and composed of four layers:
    1- A first layer of points, that are not plotted, that allowed selecting lines by proximity.
    2- The lines
    3- A point at the end of each line
    4- Text identifying the line at the end of the line
    The function also calculates the domain for the x-axis to leave space for the text'''
    
    x_var, x_axis = set_x_axis(x_option)
    
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

def map_chart_f(scope,data_all,y_map_var,region_title,multiselection,regions):

    json_root = "https://raw.githubusercontent.com/deldersveld/topojson/master/"
    world_json = json_root+"world-countries-sans-antarctica.json"
    spain_json = json_root+"countries/spain/spain-comunidad-with-canary-islands.json"

    if scope == "World":   
        source = alt.topo_feature(world_json,'countries1')
        scale_map=alt.Scale(domain=[0,100000])
    else:        
        source = alt.topo_feature(spain_json,'ESP_adm1')
        scale_map=alt.Scale(domain=[0,10000])

    list_dates = data_all.loc[data_all[region_title]==multiselection[0],"Date_N"].to_list()
    
    dates_step = max(ceil(len(regions)*len(list_dates)/5000),3)
    list_dates = list_dates[::dates_step]
    data_all = data_all[data_all.Date_N.isin(list_dates)]
    
    # Igual quitar los países que no tengan apenas nada en la última fecha    
    slider = alt.binding_range(min=list_dates[0], max=list_dates[-1], step=dates_step, name='Day in available range:')
    selector = alt.selection_single(name="Date_N", fields=['Date_N'],
                            bind=slider,init={'Date_N':1})

    
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
    
    return map_chart

# class AreaChart(alt.Chart):
#     # or should it be a class?? so i can call method line or not. Let's try with a class
#     def __init__(self,df_covid19_region,region_title,x_var,y_vars,stack,solve_y_scale):
#         base = (
#             alt.Chart(df_covid19_region)
#             .encode(            
#                 x=x_var,
#             ).properties(
#                 height=150,
#                 width=180,
#         ))
#         area = (
#             base.mark_area(opacity=0.7,line=True)
#             .transform_fold(y_vars)
#             .encode(
#                 alt.Y('value:Q',stack=stack,axis=alt.Axis(title='count')),
#                 color=alt.Color('key:N',
#                         scale=alt.Scale(
#                             range=['#1f77b4','#e41a1c','#71f594']),
#                         legend=alt.Legend(title=None)),
#                 tooltip=[x_var,'value:Q'],
#             ))

#         if solve_y_scale:
#             y_scale_rs = "independent"
#         else:
#             y_scale_rs = "shared"

#         self = (area.facet(
#             facet=region_title+':N',
#             columns=3,
#             ).resolve_scale(y=y_scale_rs))

#     def order(self,dict):
#         self.transform_calculate(order=dict).encode(order = "order:Q")
#     def line(self,y_var,**kwargs):
#         self.mark_line().encode(
#             alt.Y("Active Cases:Q",axis=alt.Axis(title='count')),
#             color=alt.value('black'),
#             size = alt.value(2),
#             shape=alt.Shape('Active_cases_label', legend=alt.Legend(title=None))
#         )



def area_chart_f(df_covid19_region,region_title,x_option,y_vars,stack,solve_y_scale,order_var,*y_line_var):

    x_var, x_axis = set_x_axis(x_option)

    base = (
        alt.Chart(df_covid19_region)
        .encode(            
            x=x_axis,
        ).properties(
            height=150,
            width=180,
    ))

    area = (
        base.mark_area(opacity=0.7,line=True)
        .transform_fold(y_vars)
        .encode(
            y=alt.Y('value:Q',stack=stack,axis=alt.Axis(title='count')),
            color=alt.Color('key:N',
                    scale=alt.Scale(
                        range=['#1f77b4','#e41a1c','#71f594']),
                    legend=alt.Legend(title=None)),
            tooltip=[x_var,'value:Q'],
        ))

    # order parameter. Either we do simple ordering or we give a dictionary with custom order
    if isinstance(order_var,str):        
        area = area.transform_calculate(
            order=order_var,
        ).encode(
            order= "order:Q"
        )
    else:        
        area = area.encode(
            order = "key:N",
        )

    # add a line if requested
    if y_line_var:        
        line_st_3 =(
            base.mark_line()
            .encode(
                alt.Y(y_line_var[0]+":Q",axis=alt.Axis(title='count')),
                color=alt.value('black'),
                size = alt.value(2),
                shape=alt.Shape('Active_cases_label', legend=alt.Legend(title=None))
            ))
        area = alt.layer(                    
                area,
                line_st_3,
                )


    # Facet construction
    if solve_y_scale:
        y_scale_rs = "independent"
    else:
        y_scale_rs = "shared"

    area = (
        area.facet(
            facet=region_title+':N',
            columns=3
        ).resolve_scale(y=y_scale_rs)
    )

    return area
