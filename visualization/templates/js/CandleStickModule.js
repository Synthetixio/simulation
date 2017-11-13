var CandleStickModule = function(series, width, height) {
	let graph_id = (series[0].Label).replace(/[^a-zA-Z]/g, "");
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

	var chart = new Chart(context, {type: 'financial', data: data, options: options});

	this.render = function(step, data) {
		chart.data.labels.push(step);
		chart.data.datasets = [];
		for (let i=0; i<data.length; i++) {
			chart.data.datasets.push({data: []});
            for (let j = 0; j < data[i].length; j++) {
                chart.data.datasets[i].data.push({
                    h: data[i][j][0],
                    l: data[i][j][1],
                    o: data[i][j][2],
                    c: data[i][j][3]
                });
        	}
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
