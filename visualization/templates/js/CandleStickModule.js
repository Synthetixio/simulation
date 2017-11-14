var CandleStickModule = function(label, width, height, line_colour, bar_colour) {
	let graph_id = (label).replace(/[^a-zA-Z]/g, "");
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
	var datasets = [
		{
			label: label,
			data: [],
			type: 'financial',
		},
		{
			label: 'Rolling average',
			data: [],
			type: 'line',
			backgroundColor: line_colour,
			borderColor: line_colour,
			fill: false,
			pointRadius: 0
		},
		{
			label: 'Volume',
			data: [],
			type: 'bar',
			backgroundColor: bar_colour,
			borderColor: bar_colour,
			fill: true,
		}
	];

	var data = {
		labels: [],
		datasets: datasets,

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
				display: false,
				stacked: true
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

	var chart = new Chart(context, {type: 'financial', data: data, options: options});
	chart.last_ticks = ['0', '2'];

	this.render = function(step, data) {
		chart.data.labels = [];
		chart.data.datasets[0].data = [];
		chart.data.datasets[1].data = [];
		chart.data.datasets[2].data = [];

		let candle_data = data[0];
		let price_data = data[1];
		let vol_data = data[2];

		var max_vol = vol_data.reduce(function(a, b) {
			return Math.max(a, b);
		});

		let vol_percentages = [];
		for (let i in vol_data) {
			if (max_vol == 0) {
				vol_percentages.push(0);
			} else {
                vol_percentages.push(vol_data[i] / max_vol);
            }
		}

		let tick_data = data[3];
		let start = 0;
		// if (candle_data.length > 85) {
		// 	  start = candle_data.length - 85;
		// }
		for (let i=start; i<candle_data.length; i++) {
			if (candle_data[i][3] < 0) {
				if (i > 0) {
					candle_data[i][1] = candle_data[i-1][1];
					candle_data[i][2] = candle_data[i-1][2];
					candle_data[i][3] = candle_data[i-1][3]
				} else {
					break;
				}
			}
			chart.data.labels.push(tick_data[i]);
			chart.data.datasets[0].data.push({
				o: candle_data[i][0],
				c: candle_data[i][1],
				h: candle_data[i][2],
				l: candle_data[i][3],
				t: tick_data[i],
				v: vol_data[i],
				p: price_data[i]
			});

			chart.data.datasets[1].data.push(price_data[i]);

			let min = parseFloat(chart.last_ticks[chart.last_ticks.length-1]);
			let max = parseFloat(chart.last_ticks[0]);
			chart.data.datasets[2].data.push(min + ((max-min) * vol_percentages[i]));

		}

		chart.update();
		chart.last_ticks = chart.scales['y-axis-0'].ticks;

	};

	this.reset = function() {
		data.labels = [];
		for (let i=0; i<chart.data.datasets.length; i++) {
			chart.data.datasets[i].data = [];
		}
	};
};
