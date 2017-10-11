// BarGraphModule.js


var BarGraphModule = function(graph_id, num_agents, width, height) {

    // Create the elements
    // Create the tag:
    let div_tag = "<div id='"+graph_id+"' class='ct-chart'></div>";
    // Append it to body:
    let div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:
    let dataseries = [];
    // add 0 for each bin, and a bin label
    bins = [];
    for (let i=0; i<num_agents; i++) {
        dataseries.push(num_agents - i);
        bins.push(i);
    }
    let data = {
      labels: bins,
      series: [dataseries]
    };


    let options = {
      fullWidth: true,
      height: height+'px',
      chartPadding: {
        right: 40
      },
      plugins: [Chartist.plugins.tooltip()]
    };
    // Create the chart object
    var chart = new Chartist.Bar('#'+graph_id, data, options);

    this.render = function(new_data) {
        // function to modify the chart data
        this.reset();

        for (let i = 0; i < new_data.length; i++) {
          chart.data.series[0][i] = {meta: new_data[i][0], value: new_data[i][1]};
          chart.data.labels[i] = i;
        }

        chart.update();
    };

    this.reset = function() {
        for (let i in chart.data.series[0]) {
            chart.data.series[0][i] = 0;
        }
    };
};
