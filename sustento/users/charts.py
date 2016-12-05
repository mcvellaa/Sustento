from highcharts import Highchart

# from .models import *

# A chart is the container that your data will be rendered in, it can (obviously) support multiple data series within it.
chart = Highchart()

options = {
    'title': {
        'text': 'Daily Emotion Analysis'
    },
    'xAxis': {
        'reversed': False,
        'title': {
            'enabled': True,
            'text': 'Time'
        },
        'labels': {
            'formatter': 'function () {\
                return this.value;\
            }'
        },
        'maxPadding': 0.05,
        'showLastLabel': True
    },
    'yAxis': {
        'title': {
            'text': 'Emotion Score'
        },
        'labels': {
            'formatter': "function () {\
                return this.value + '°';\
            }"
        },
        'lineWidth': 2
    },
    'legend': {
        'enabled': False
    },
    'tooltip': {
        'headerFormat': '<b>{series.name}</b><br/>',
        'pointFormat': '{point.x} km: {point.y}°C'
    }
}

chart.set_dict_options(options)
data = [[1,2], [0.5, 3]]

# pjs = PersonalJournal.objects.all()
# for p in  pjs:
# 	data.append([p.print_chart_time, p.emotion_sadness])

chart.add_data_set(data, 'scatter', 'Outlier', 
    marker={
        'fillColor': 'white',
        'lineWidth': 1,
        'lineColor': 'Highcharts.getOptions().colors[0]'
    },
    tooltip={'pointFormat': 'Observation: {point.y}'}
)

chart.save_file()
