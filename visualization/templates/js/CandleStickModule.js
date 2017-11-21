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
	var graph_length = 20;
	var chart = new Chart(context, {type: 'financial', data: data, options: options});
	chart.last_ticks = ['0', '2'];

	this.render = function(step, data) {
		if (data.length < 1) {
			return false;
		}

		chart.data.labels = [];
		chart.data.datasets[0].data = [];
		chart.data.datasets[1].data = [];
		chart.data.datasets[2].data = [];

		max_vol = 0;
		for (let i in data) {
			if (data[i][2] > max_vol) {
				max_vol = data[i][2];
			}
		}

		let vol_percentages = [];
		for (let i in data) {
			if (max_vol === 0) {
				vol_percentages.push(0);
			} else {
                vol_percentages.push(data[i][2] / max_vol);
            }
		}

		let start = data.length - graph_length;
		if (start < 0) {
			for (let i=start; i<0; i++) {
				// use filler data of 1 or 0
				chart.data.datasets[0].data.push({
					o: 1,
					c: 1,
					h: 1,
					l: 1,
					t: i,
					v: 0,
					p: 0
				});
				chart.data.datasets[1].data.push(NaN);
				chart.data.datasets[2].data.push(0);
				chart.data.labels.push(i);
			}
			start = 0;
		}
		for (let i=start; i<data.length; i++) {
			let candle_data = data[i][0];
			let price_data = data[i][1];
			let vol_data = data[i][2];
			if (candle_data[3] < 0) {
				if (i > 0) {
					candle_data[1] = data[i-1][0][1];
					candle_data[2] = data[i-1][0][2];
					candle_data[3] = data[i-1][0][3]
				} else {
					break;
				}
			}
			chart.data.labels.push(i);
			chart.data.datasets[0].data.push({
				o: candle_data[0],
				c: candle_data[1],
				h: candle_data[2],
				l: candle_data[3],
				t: i,
				v: vol_data,
				p: price_data
			});

			chart.data.datasets[1].data.push(price_data);

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
		chart.update();
	};
};
