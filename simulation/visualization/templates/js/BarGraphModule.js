// BarGraphModule.js

var BarGraphModule = function (graph_id, width, height) {
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

	var data = {
		labels: [],
		datasets: []
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
				display: false,
				stacked: true
			}],
			yAxes: [{
				display: true,
                stacked: true
			}]
		},
		animation: false
	};
    // Create the chart object
	var chart = new Chart(context, {type: 'bar', data: data, options: options});

    this.render = function (step, new_data) {
        // data should be in the form:
        // [data_labels, bar_labels, data_colors, dataset1, ...]
        this.reset();

        if (new_data.length >= 3) {
            let data_labels = new_data[0];
            let data_colors = new_data[1];
            let data_stack = new_data[2];
            let bar_labels = new_data[3];

            for (let i in bar_labels) {
                chart.data.labels[i] = bar_labels[i];
            }

            for (let i = 4; i < new_data.length; i++) {
                chart.data.datasets.push({
                    label: data_labels[i-4],
                    backgroundColor: data_colors[i-4],
                    borderColor: data_colors[i-4],
                    stack: data_stack[i-4],
                    fill: true,
                    pointRadius: 0,
                    data: []
                });
            }

            // meta is the "label" that shows up when hovering
            for (let i = 4; i < new_data.length; i++) {
                for (let j = 0; j < new_data[i].length; j++) {
                    chart.data.datasets[i - 4].data.push(this.round(new_data[i][j]));
                }
            }

        }
        chart.update();
    };

    this.reset = function () {
        chart.data.datasets = [];
        chart.data.labels = [];
    };

    this.round = function (value) {
        return Math.floor(value*10000)/10000
    };
};
