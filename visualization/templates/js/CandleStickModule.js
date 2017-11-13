function randomNumber(min, max) {
	return Math.random() * (max - min) + min;
}

function randomBar(date, lastClose) {
	var open = randomNumber(lastClose * .95, lastClose * 1.05);
	var close = randomNumber(open * .95, open * 1.05);
	var high = randomNumber(Math.max(open, close), Math.max(open, close) * 1.1);
	var low = randomNumber(Math.min(open, close) * .9, Math.min(open, close));
	return {
		t: date,
		o: open,
		h: high,
		l: low,
		c: close
	};
}

var data = [randomBar(1, 30)];
var labels = [0];
tick = 0;
while (data.length < 60) {
	tick += 1;
    data.push(randomBar(tick, data[data.length - 1].c));
    labels.push(tick)
}

var ctx = document.getElementById("chart1").getContext("2d");
ctx.canvas.width = 1000;
ctx.canvas.height = 300;
new Chart(ctx, {
	type: 'financial',
	data: {
		datasets: [{
			label: "Chart",
            labels: labels,
			data: data
		}]
	}
});