var ChartModule = function(group, title, desc, series, width, height) {
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

	var datasets = [];
	for (var i in series) {
		var s = series[i];
		var new_series = {
			name: s.Label,
			color: s.Color,
			fill: false,
		};
		datasets.push(new_series);
	}

	// Create the context and the drawing controller:
	var chart = Highcharts.chart(graph_id, {
		plotOptions: {
			line: {
				marker: {
					enabled: false
				}
			}
		},

		title: {
			text: title
		},

		legend: {
			layout: 'vertical',
			align: 'right',
			verticalAlign: 'middle'
		},

		tooltip: {
			shared: true
		},

		series: datasets,
		chart: {
			animation: false,
            height: 250,
			min : 0,
			zoomType: 'x',
		},
        credits: {
			enabled: false
		},
		xAxis: {
			allowDecimals: false,
		}

	});

	this.render = function(force_draw, data) {

	    if (div.hasClass("hidden")) {
	        chart.was_hidden = true;
	        return false;
        }

		if (data.length < 1) {
			return false;
		}

        if (force_draw || chart.was_hidden || data.length < 5) {
			for (let j in data[0]) {
				let _data = [];
                for (let i = 0; i < data.length; i++) {
                    _data.push([i, data[i][j]]);
                }
                chart.series[j].setData(_data)
            }

        }

        chart.was_hidden = false;
	};

	this.reset = function() {
	};
};