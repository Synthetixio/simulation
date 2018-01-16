// BarGraphModule.js

var BarGraphModule = function (group, title, desc, label, width, height) {
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

    // Create the chart object
	var chart = Highcharts.chart(graph_id, {
	    title: {
	        text: title
        },
        chart: {
			animation: false,
            height: 250,
            min : 0,
            zoomType: 'x',
		},
        credits: {
			enabled: false
		},

    });
    var chart_setup = false;

    this.render = function (force_draw, data) {

	    if (div.hasClass("hidden")) {
	        chart.was_hidden = true;
	        return false;
        }

        let new_data;

        if (data.length < 1) {
            return false;
        }

        if (chart_setup === false && data.length > 0) {
            chart = this.create_chart(data[0]);
            chart_setup = true;
        }

        if (chart.was_hidden || force_draw) {
            if (data.length > 1) {
                new_data = data[data.length - 1];
            } else {
                new_data = [];
                for (let i = 4; i < data[0].length; i++) {
                    new_data.push(data[0][i])
                }
            }

            if (new_data.length >= 1) {
                for (let i = 0; i < new_data.length; i++) {
                    let _data = [];
                    for (let j = 0; j < new_data[i].length; j++) {
                        _data.push(this.round(new_data[i][j]))
                    }
                    chart.series[i].setData(_data);
                }
            }
        }
        chart.was_hidden = false;
    };

    this.reset = function () {
        chart_setup = false;
    };

    this.round = function (value) {
        return Math.floor(value*1000)/1000
    };

    this.create_chart = function(label_data) {
        let options = chart.options;

        let data_labels = label_data[0];
        let data_colors = label_data[1];
        let data_stacks = label_data[2];

        // player names
        options.xAxis.categories = label_data[3];
        options.series = [];

        for (let i = 0; i < label_data[0].length; i++) {
            options.series.push({
                name: data_labels[i],
                color: data_colors[i],
                stack: data_stacks[i],
                data: []
            })
        }

        options.plotOptions = {
            column: {
                stacking: 'normal',
                pointPadding: 0.2,
                borderWidth: 0
            }
        };

        options.chart = {
            type: 'column',
            animation: false,
            height: 300
        };

        options.tooltip = {
            shared:true,
            followPointer: true,
            formatter:
                function () {
                    let result = '<b>' + chart.options.xAxis.categories[this.x] + '</b><br/>';
                    for (let i in chart.series) {
                        // could add some variable for using absolute values in the constructor, but for now
                        // all the graphs want to.
                        result += chart.series[i].name + ': ' + Math.abs(chart.series[i].data[this.x].y) + '<br/>';
                    }
                    return result;
                }
        };

        return Highcharts.chart(chart.renderTo.id, options);
    }
};
