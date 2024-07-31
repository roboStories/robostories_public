import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import requests
from collections import deque
import sys
from signals import Signal
from datetime import datetime


####

# TODOs
# - reorganize the classes structure, to become more usable and better organized
# - write the data from all the sensors into csv file

####

class SensorSignal:
    __keyTDht:str = 'tDht'
    __keyTBmp:str = 'tBmp'
    __keyTComp:str = 'tComp'
    __keyHDht:str = 'hDht'
    __keyPBmp:str = 'pBmp'

    def __init__(self, maxLen:int = 1440) -> None:
        self.tDht:Signal = Signal(maxLen=maxLen)
        self.tBmp:Signal = Signal(maxLen=maxLen)
        self.tComp:Signal = Signal(maxLen=maxLen)
        self.hDht:Signal = Signal(maxLen=maxLen)
        self.pBmp:Signal = Signal(maxLen=maxLen)
        self.ts:list[int] = deque(maxlen=maxLen)

    def updateVals(self, dataIn:dict, tsIn:int):
         self.tDht.updateVals(dataIn.get(self.__keyTDht, {}))
         self.tBmp.updateVals(dataIn.get(self.__keyTBmp, {}))
         self.tComp.updateVals(dataIn.get(self.__keyTComp, {}))
         self.hDht.updateVals(dataIn.get(self.__keyHDht, {}))
         self.pBmp.updateVals(dataIn.get(self.__keyPBmp, {}))
         self.ts.append(tsIn)

    def getKeys(self):
        # mind order!
        return self.__keyTDht, self.__keyTBmp, self.__keyTComp, self.__keyHDht, self.__keyPBmp
    
    def getErrVals(self):
        # mind order!
        return \
                [self.tDht.nanCnt, self.tDht.grdCnt], \
                [self.tBmp.nanCnt, self.tBmp.grdCnt], \
                [self.tComp.nanCnt, self.tComp.grdCnt], \
                [self.hDht.nanCnt, self.hDht.grdCnt], \
                [self.pBmp.nanCnt, self.pBmp.grdCnt]
        
def getSunsetSunrise(lat:str, lng:str):
    url = f'https://api.sunrisesunset.io/json?lat={lat}&lng={lng}'
    try:
        response = requests.get(url)
        data = response.json()
        
        sunrise = data['results']['sunrise']
        sunset = data['results']['sunset']
        firstLight = data['results']['first_light']
        lastLight = data['results']['last_light']
        dawn = data['results']['dawn']
        dusk = data['results']['dusk']
        
        return sunrise, sunset, firstLight, lastLight, dawn, dusk
    except Exception as e:
        print(f"Error fetching sunrise/sunset data: {e}")
        return None, None, None, None, None, None

def generate_error_bar_chart(sensData:list[SensorSignal]):
    sensKeys = ["R_" + str(i+1) for i in range(len(sensData))]
    bar_data = []
    for i,sensKey in enumerate(sensKeys):
        signalKeys:list[str] = sensData[i].getKeys()
        for j, errCnt in enumerate(sensData[i].getErrVals()):
            errKeys = sensData[i].tBmp.getKeys()    # assuming all the sensor signals are of the same Signal class
            for k, err in enumerate(errCnt):
                bar_data.append(go.Bar(
                    name=f'{sensKey} {signalKeys[j]} {errKeys[k]}',
                    x=[f'{sensKey} {signalKeys[j]} {errKeys[k]}'],
                    y=[err[-1]]))
            
    
    error_fig = {
        'data': bar_data,
        'layout': go.Layout(
            title='Error Counters',
            xaxis=dict(title='Sensor and Signal'),
            yaxis=dict(title='Error Count'),
            barmode='group'
        )
    }

    return error_fig

###################### SETUP ######################
# Initialize app config
sensIpAddr:list[str] = sys.argv[1].split(',')
lat:str = sys.argv[2].replace(" ", "").split(",")[0]
lng:str = sys.argv[2].replace(" ", "").split(",")[1]

# Initialize the Dash app
app = dash.Dash(__name__)

# Deques to store the last 100 data points
MAXLEN_DISPLAY:int = 1440 # 24h window
sensData = [SensorSignal(maxLen=MAXLEN_DISPLAY) for _ in sensIpAddr]
sunrise, sunset, firstLight, lastLight, dawn, dusk = getSunsetSunrise(lat=lat,  lng=lng)

# Define the layout of the Dash app
app.layout = html.Div([
    html.H3("Home Weather Station"),
    html.Div([
        html.P(f"Sunrise: {sunrise}"),
        html.P(f"Sunset: {sunset}"),
        html.P(f"First Light: {firstLight}"),
        html.P(f"Last Light: {lastLight}"),
        html.P(f"Dawn: {dawn}"),
        html.P(f"Dusk: {dusk}"),
    ]),
    dcc.Graph(id='temperature-chart'),
    dcc.Graph(id='humidity-chart'),
    dcc.Graph(id='pressure-chart'),
    dcc.Graph(id='error-counters-chart'),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # Poll every 10 seconds
        n_intervals=0
    )
])

# Define callback to update charts
@app.callback(
    [
        Output('temperature-chart', 'figure'),
        Output('humidity-chart', 'figure'),
        Output('pressure-chart', 'figure'),
        Output('error-counters-chart', 'figure')
     ],
    [Input('interval-component', 'n_intervals')]
)
def update_charts(n_intervals):
    # update sunrise/sunset times every x cycles
    if n_intervals%10 == 0:
        global sunrise, sunset, firstLight, lastLight, dawn, dusk
        sunrise, sunset, firstLight, lastLight, dawn, dusk = getSunsetSunrise(lat=lat,  lng=lng)

    dataFetched:int = 0
    for i, ip in enumerate(sensIpAddr):
        # Poll the sensor data
        try:
            response = requests.get('http://' + ip + '/data')
            data = response.json()
            # Update temperature and humidity data
            sensData[i].updateVals(data, datetime.now().isoformat())
            dataFetched += 1
        except Exception as e:
            print(f"Error fetching data: {e}")

    if dataFetched == len(sensIpAddr):
        pass
        # write the csv data

    # Create the temperature and humidity chart
    dataTemp = []
    dataTemp.extend([go.Scatter(x=list(sensData[i].ts), y=list(sensData[i].tDht.val), mode='lines+markers', name='T_dht_R_' + str(i+1)) for i in range(len(sensIpAddr))])
    dataTemp.extend([go.Scatter(x=list(sensData[i].ts), y=list(sensData[i].tBmp.val), mode='lines+markers', name='T_bmp_R_' + str(i+1)) for i in range(len(sensIpAddr))])
    dataTemp.extend([go.Scatter(x=list(sensData[i].ts), y=list(sensData[i].tComp.val), mode='lines+markers', name='T_comp_R_' + str(i+1)) for i in range(len(sensIpAddr))])

    temp_fig = {
        'data': dataTemp,
        'layout': go.Layout(
            xaxis=dict(title='Time'),
            yaxis=dict(title='Temperature °C', side='left'),
        )
    }
    dataHumid = [go.Scatter(x=list(sensData[i].ts), y=list(sensData[i].hDht.val), mode='lines+markers', name='Humidity_R' + str(i+1)) for i in range(len(sensIpAddr))]
    humid_fig = {
        'data': dataHumid,
        'layout': go.Layout(
            xaxis=dict(title='Time'),
            yaxis=dict(title='Humidity %', side='left'),
        )
    }

    dataPres = [go.Scatter(x=list(sensData[i].ts), y=list(sensData[i].pBmp.val), mode='lines+markers', name='Pressure_R' + str(i+1)) for i in range(len(sensIpAddr))]
    pres_fig = {
        'data': dataPres,
        'layout': go.Layout(
            xaxis=dict(title='Time'),
            yaxis=dict(title='Pressure mBar', side='left'),
        )
    }
    
    # Create the error counters chart
    error_fig = generate_error_bar_chart(sensData)

    return temp_fig, humid_fig, pres_fig, error_fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')