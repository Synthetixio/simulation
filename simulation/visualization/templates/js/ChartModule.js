var ChartModule = function(series, width, height) {
	let graph_id = (series[0].Label).replace(/[^a-zA-Z]/g, "");
	console.log(graph_id);
	// Create the elements
	var button = $('<button type="button" style="display:block" class="btn btn-sm btn-pad" onclick="toggle_graph('+graph_id+')">'+graph_id+'</button>');
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
		chart.data.labels.push(step);
		for (let i=0; i<data.length; i++) {
			chart.data.datasets[i].data.push(data[i]);
		}
		chart.update();
	};

	this.reset = function() {
		data.labels = [];
		for (let i=0; i<chart.data.datasets.length; i++) {
			chart.data.datasets[i].data = [];
		}
	};
};