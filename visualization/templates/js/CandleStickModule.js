var CandleStickModule = function(group, title, desc, label, width, height, line_colour, bar_colour) {
    let group_id = (group).replace(/[^a-zA-Z]/g, "");
	let graph_id = (title).replace(/[^a-zA-Z]/g, "");
	// Create the elements
	// var button = $('<button type="button" style="display:block" class="btn btn-sm btn-pad" onclick="toggle_graph('+graph_id+')" >'+title+'</button>');
    // button.tooltip();

    var div = $("<div id='"+graph_id+"' data-for='"+group_id+"' class='graph_div hidden'></div>");

	$("#elements").append(div);
	// Create the context and the drawing controller:


    if ($("#"+group_id)[0] === undefined) {
        var group_link = $("<a href='#' onclick='show_group("+group_id+")' class=\"list-group-item\" id='"+group_id+"'>" + group + "</a>");
        $("#sidebar-list").append(group_link);
    }

	// Prep the chart properties and series:

	var chart = Highcharts.stockChart(graph_id, {
            rangeSelector: {
                selected: 30,
                inputEnabled: false,
                buttons: [{
                    type: 'millisecond',
                    count: 30,
                    text: '30'
                },
                {
                    type: 'millisecond',
                    count: 100,
                    text: '100'
                },{
                    type: 'millisecond',
                    count: 200,
                    text: '200'
                },{
                    type: 'millisecond',
                    count: 400,
                    text: '400'
                },{
                    type: 'all',
                    text: 'All'
                }
                ]
            },

            title: {
                text: title
            },

            xAxis: {
                visible: false,
                dateTimeLabelFormats: {
                    millisecond: "%L",
                    second: "%S%L",
                    minute: "%M%S%L"
                }
            },

            yAxis: [
                {
                    title: {
                        text:"Candle Data"
                    },
                    min : 0
                },
                {
                    title: {
                        text: "Volume Data"
                    },
                    opposite: true
                }
            ],

            tooltip: {
                animation: false,
                shared: true,
                dateTimeLabelFormats: {
                    millisecond: "%L",
                    second:"%S%L",
                    minute:"%M%S%L",
                    hour:"%L",
                    day:"%L",
                    week:"%L",
                    month:"%L",
                    year:"%L"
                },
            },

            navigator: {
                xAxis: {
                    visible: false
                },
                series: {
                    color: line_colour,
                }
            },
            chart: {
                animation: false,
                height: 300
            },
            credits: {
                enabled: false
            },

            dataGrouping: {
                dateTimeLabelFormats: {
                    millisecond: ['%S%L', '%S%L', '-%S%L'],
                    second: ['%S%L', '%S%L', '-%S%L'],
                    minute: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                    hour: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                    day: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                    week: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                    month: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                    year: ['%M%S%L', '%M%S%L', '-%M%S%L']
                },
            },

            series: [{
                type: 'candlestick',
                name: 'Havven Candle Data',
                min : 0,
                data: [],
                upColor: '#0F0',
                color: '#F00',
                dataGrouping: {
                    dateTimeLabelFormats: {
                        millisecond: ['%S%L', '%S%L', '-%S%L'],
                        second: ['%S%L', '%S%L', '-%S%L'],
                        minute: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                        hour: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                        day: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                        week: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                        month: ['%M%S%L', '%M%S%L', '-%M%S%L'],
                        year: ['%M%S%L', '%M%S%L', '-%M%S%L']
                    },

                },

            }, {
                type: 'line',
                name: 'Rolling Average',
                data: [],
                color: line_colour,

            }, {
                type: 'column',
                name: 'Volume',
                data: [],
                zIndex: -1,
                yAxis: 1,
                color: bar_colour
            }
            ]
        });

	this.render = function(force_draw, data) {

	    if (div.hasClass("hidden")) {
	        chart.was_hidden = true;
	        return false;
        }

		if (data.length < 1) {
			return false;
		}

        if (force_draw || chart.was_hidden) {

            let candle_data = [];
            let line_data = [];
            let bar_data = [];
            for (let i = 0; i < data.length; i++) {
                candle_data.push([i, data[i][0][0], data[i][0][2], data[i][0][3], data[i][0][1]]);
                line_data.push([i, data[i][1]]);
                bar_data.push([i, data[i][2]]);
            }


            let candle_series = chart.series[0];
            candle_series.setData(candle_data);
            let line_series = chart.series[1];
            line_series.setData(line_data);
            let bar_series = chart.series[2];
            bar_series.setData(bar_data);

        }

        if (data.length === 35 || chart.was_hidden) {
		    chart.rangeSelector.clickButton(4);
		    chart.rangeSelector.clickButton(0);
        } else if (data.length < 35) {
		    chart.rangeSelector.clickButton(0);
		    chart.rangeSelector.clickButton(4);
        }

        chart.was_hidden = false;
	};

	this.reset = function() {
		for (let i=0; i<chart.series; i++) {
			chart.series[i].setData([]);
		}
		chart.redraw()
	};
};
