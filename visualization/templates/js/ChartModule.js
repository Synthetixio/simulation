var ChartModule = function(desc, series, width, height) {
	let graph_id = (series[0].Label).replace(/[^a-zA-Z]/g, "");
	// Create the elements
	var button = $('<button type="button" style="display:block" class="btn btn-sm btn-pad" onclick="toggle_graph('+graph_id+')" data-toggle="tooltip" title="'+desc+'">'+graph_id+'</button>');
    button.tooltip();
    var div = $("<div id='"+graph_id+"' class=''></div>");

	// Create the tag:
	var canvas_tag = "<canvas width='" + width + "' height='" + height + "' ";
	canvas_tag += "style='border:1px dotted'></canvas>";
	// Append it to body:
	var canvas = $(canvas_tag)[0];
	div.append(canvas);
	//$("body").append(canvas);
	$("#elements").append(button);
	$("#elements").append(div);
	// Create the context and the drawing controller:
	var context = canvas.getContext("2d");

	// Prep the chart properties and series:
	var datasets = [];
	for (var i in series) {
		var s = series[i];
		var new_series = {
			label: s.Label,
			backgroundColor: s.Color,
			borderColor: s.Color,
			fill: false,
			pointRadius: 0,
			data: []
		};
		datasets.push(new_series);
	}

	var data = {
		labels: [],
		datasets: datasets
	};

	var options = {
		responsive: true,
		maintainAspectRatio: false,

		tooltips: {
			enabled: false,
			mode: 'index',
			intersect: false,
			position: "nearest"
		},
		hover: {
			mode: 'nearest',
			intersect: true
		},
		scales: {
			xAxes: [{
				display: true,
			}],
			yAxes: [{
				display: true
			}]
		},
		elements: {
            line: {
                tension: 0, // disables bezier curves
            }
        },
		animation: false
	};

	var chart = new Chart(context, {type: 'line', data: data, options: options});

	this.render = function(step, data) {
        chart.data.labels = [];
		for (let i in chart.data.datasets) {
            chart.data.datasets[i].data = []
        }

        for (let j in data) {
			chart.data.labels.push(j);
		}

        for (let i in chart.data.datasets) {
			for (let j in data) {
				chart.data.datasets[i].data.push(data[j][i])
			}
		}

		chart.update();
	};

	this.reset = function() {
		chart.data.labels = [];
		for (let i in chart.data.datasets) {
            chart.data.datasets[i].data = []
        }
        chart.update();
	};
};