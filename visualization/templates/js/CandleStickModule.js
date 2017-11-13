var CandleStickModule = function(label, width, height) {
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
	var datasets = [{label: "Graph", data: []}];

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
				display: false,
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

	this.render = function(step, data) {

		chart.data.labels = [];
		chart.data.datasets[0].data = [];
		for (let i=0; i<data.length; i++) {
			if (data[i][3] < 0) {
				if (i > 0) {
					data[i][1] = data[i-1][1];
					data[i][2] = data[i-1][2];
					data[i][3] = data[i-1][3]
				} else {
					break;
				}
			}
			chart.data.labels.push(i+1);
			chart.data.datasets[0].data.push({
				o: data[i][0],
				c: data[i][1],
				h: data[i][2],
				l: data[i][3],
				t: i+1
			});

		}
		chart.update();
		console.log(chart.data)
	};

	this.reset = function() {
		data.labels = [];
		for (let i=0; i<chart.data.datasets.length; i++) {
			chart.data.datasets[i].data = [];
		}
	};
};
