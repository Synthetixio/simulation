// BarGraphModule.js


var BarGraphModule = function (graph_id, num_agents, width, height) {

    // Create the elements
    // Create the tag:
    let div_tag = "<div id='" + graph_id + "' class='ct-chart'></div>";
    // Append it to body:
    let div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:

    let data = {
        labels: [],
        series: [[]]
    };


    let options = {
        stackBars: true,
        fullWidth: true,
        height: height + 'px',
        chartPadding: {
            right: 40
        },
        plugins: [Chartist.plugins.tooltip()]
    };
    // Create the chart object
    var chart = new Chartist.Bar('#' + graph_id, data, options);

    this.render = function (new_data) {
        // data should be in the form:
        // [data_labels, bar_labels, dataset1, ...]

        this.reset();

        if (new_data.length >= 2) {
            let data_labels = new_data[0];
            let bar_labels = new_data[1];

            for (let i = 2; i < new_data.length; i++) {
                chart.data.series.push([]);
            }

            // meta is the "label" that shows up when hovering
            for (let i = 2; i < new_data.length; i++) {
                for (let j = 0; j < new_data[i].length; j++) {
                    if (data_labels.length > 0) {
                        chart.data.series[i - 2][j] = {meta: data_labels[i - 2], value: new_data[i][j]};
                    } else {
                        chart.data.series[i - 2][j] = {meta: bar_labels[j], value: new_data[i][j]};
                    }
                }
            }

            for (let i in bar_labels) {
                chart.data.labels[i] = i;
            }

        }

        chart.update();
    };

    this.reset = function () {
        chart.data.series = [];
        chart.data.labels = [];
    };
};
