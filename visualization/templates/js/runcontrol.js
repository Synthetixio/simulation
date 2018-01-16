/** runcontrol.js

 Users can reset() the model, advance it by one step(), or run() it through. reset() and
 step() send a message to the server, which then sends back the appropriate data. run() just
 calls the step() method at fixed intervals.

 The model parameters are controlled via the MesaVisualizationControl object.
 */

/**
 * Object which holds visualization parameters.
 *
 * tick: What tick of the model we're currently at
 running: Boolean on whether we have reached the end of the current model
 * fps: Current frames per second.
 */

var fps_max = $('#fps_max')[0].content;
var fps_default = $('#fps_default')[0].content;

var MesaVisualizationControl = function () {
    this.draw_delay_period = 5;
    this.tick = -1; // Counts at which tick of the model we are.
    this.last_sent = -1;
    this.run_number = 0;
    this.running = false; // Whether there is currently a model running
    this.done = false;
    this.fps = fps_default; // Frames per second
    this.data = []
};

var player; // Variable to store the continuous player
var control = new MesaVisualizationControl();
var elements = [];  // List of Element objects
var model_params = {};
var group_changed = false;

// Playback buttons
var playPauseButton = $('#play-pause');
var stepButton = $('#step');
var backButton = $('#back');
var resetButton = $('#reset');

var fpsControl = $('#fps').slider({
    max: fps_max,
    min: 1,
    value: fps_default,
    ticks: [1, fps_max],
    ticks_labels: [1, fps_max],
    ticks_position: [0, 100]
});

// Sidebar dom access
var sidebar = $("#settings_body");

var agent_settings = $("#agent_settings");
var agent_values = {};

// Open the websocket connection; support TLS-specific URLs when appropriate
var ws = new WebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");

ws.onopen = function () {
    console.log("Connection opened!");
    send({"type": "get_params"}); // Request model parameters when websocket is ready
    reset();
    single_step();
    control.tick -= 1; // leave tick at -1 for now
};

// Add model parameters that can be edited prior to a model run
var initGUI = function () {

    var onSubmitCallback = function (param_name, value) {
        send({"type": "submit_params", "param": param_name, "value": value});
    };

    var addBooleanInput = function (param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        var checkbox = $("<input class='model-parameter' id='" + dom_id + "' type='checkbox'/>")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(checkbox);
        $(checkbox).bootstrapSwitch({
            'state': obj.value,
            'size': 'small',
            'onSwitchChange': function (e, state) {
                onSubmitCallback(param, state);
            }
        });
    };

    var addNumberInput = function (param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        var number_input = $("<input class='model-parameter' id='" + dom_id + "' type='number'/>")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(number_input);
        $(number_input).val(obj.value);
        $(number_input).on('change', function () {
            onSubmitCallback(param, Number($(this).val()));
        })
    };

    var addSliderInput = function (param, obj) {
        var dom_id = param + '_id';
        var label = $("<p></p>")[0];
        var tooltip = $("<a data-toggle='tooltip' data-placement='top' class='label label-primary'>" + obj.name + "</a>")[0];
        if (obj.description !== null) {
            $(tooltip).tooltip({
                title: obj.description,
                placement: 'right'
            });
        }
        label.append(tooltip);
        var slider_input = $("<input id='" + dom_id + "' type='text' />")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(slider_input);
        $(slider_input).slider({
            min: obj.min_value,
            max: obj.max_value,
            value: obj.value,
            step: obj.step,
            ticks: [obj.min_value, obj.max_value],
            ticks_labels: [obj.min_value, obj.max_value],
            ticks_positions: [0, 100]
        });
        $(slider_input).on('change', function () {
            onSubmitCallback(param, Number($(this).val()));
        })
    };

    var addChoiceInput = function (param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        sidebar.append(label);

        var dropdown = $("<div class='dropdown'></div>")[0];
        var button = $("<button class='btn btn-default dropdown-toggle' type='button' data-toggle='dropdown'></button>")[0];
        var span = $("<span class='caret'></span>")[0];
        $(button).text(obj.value + " ");
        $(button).id = dom_id;
        $(button).append(span);
        var choice_container = $("<ul class='dropdown-menu' role='menu' aria-labelledby='" + dom_id + "'></ul>")[0];
        for (var i = 0; i < obj.choices.length; i++) {
            var choice = $("<li role='presentation'><a role='menuitem' tabindex='-1' href='#'>" + obj.choices[i] + "</a></li>")[0];
            $(choice).on('click', function () {
                var value = $(this).children()[0].text;
                $(button).text(value + ' ');
                onSubmitCallback(param, value);
            });
            choice_container.append(choice);
        }

        dropdown.append(button);
        dropdown.append(choice_container);
        sidebar.append(dropdown);
    };

    var addTextBox = function (param, obj) {
        var well = $('<div class="well">' + obj.value + '</div>')[0];
        sidebar.append(well);
    };

    var addAgentSliders = function (param, obj) {
        // this will assume only one of these exists

        let data = obj.value;

        let min_val = 0;
        let max_val = 100;
        let step = 0.01;

        let slider_objs = {};

        for (let i in data) {
            agent_values[i] = data[i].value;
            let dom_id = param + "_" + i;
            let label = $("<p></p>")[0];
            let tooltip = $("<a data-toggle='tooltip' data-placement='top' class='label label-primary'>" + i + "</a>")[0];
            if (data[i].description !== undefined) {
                $(tooltip).tooltip({
                    title: data[i].description,
                    placement: 'right'
                });
            }
            label.append(tooltip);

            let slider_input = $("<input class='agent_sliders' id='" + i + "' type='text'/>")[0];
            let input_group = $("<div class='input-group input-group-lg'></div>")[0];
            agent_settings.append(input_group);
            input_group.append(label);
            input_group.append(slider_input);

            slider_objs[i] = slider_input;

            $(slider_input).slider({
                name: i,
                min: min_val,
                max: max_val,
                value: parseFloat(data[i]) * max_val,
                step: step,
                ticks: [min_val, max_val],
                ticks_labels: [min_val, max_val],
                ticks_positions: [0, 100],
                width: '100%'
            });
            $(slider_input).on('change', function () {
                var slider = $(slider_input)[0];
                var sum = 0;
                var sum_others = 0;

                var slider_group = $(".agent_sliders");

                for (let i in slider_objs) {
                    let item = $(slider_objs[i])[0];
                    if (item !== slider) {
                        sum_others += parseFloat(item.value);
                    }
                    sum += parseFloat(item.value);
                }

                let return_val = {};

                slider_group.each(function () {
                    let item = $(this)[0];
                    if (item !== slider) {
                        let diff = max_val - sum;
                        $(item).slider('setValue', parseFloat(item.value) + (parseFloat(item.value) / sum_others) * diff);
                    }
                    return_val[item.id] = parseFloat(item.value) / max_val;
                });

                onSubmitCallback(param, return_val);
            })
        }
    };

    var addParamInput = function (param, option) {
        switch (option['param_type']) {
            case 'checkbox':
                addBooleanInput(param, option);
                break;

            case 'slider':
                addSliderInput(param, option);
                break;

            case 'choice':
                addChoiceInput(param, option);
                break;

            case 'number':
                addNumberInput(param, option);   // Behaves the same as just a simple number
                break;

            case 'static_text':
                addTextBox(param, option);
                break;

            case 'agent_fractions':
                addAgentSliders(param, option);
                break;
        }
    };

    for (var option in model_params) {

        var type = typeof(model_params[option]);
        var param_str = String(option);

        switch (type) {
            case "boolean":
                addBooleanInput(param_str, {'value': model_params[option], 'name': param_str});
                break;
            case "number":
                addNumberInput(param_str, {'value': model_params[option], 'name': param_str});
                break;
            case "object":
                addParamInput(param_str, model_params[option]);    // catch-all for params that use Option class
                break;
        }
    }
};

/** Parse and handle an incoming message on the WebSocket connection. */
ws.onmessage = function (message) {
    var msg = JSON.parse(message.data);
    console.log(msg);
    switch (msg["type"]) {
        case "viz_state":
            // ignore any old data
            var run_num = msg["run_num"];
            if (parseInt(run_num) !== control.run_number) {
                break;
            }

            var data = msg["data"];
            for (var i in data) {
                let step = data[i][0];
                let dataset = data[i][1];

                if (control.data.length <= step) {
                    control.data.push(dataset);
                }
            }
            break;
        case "end":
            // We have reached the end of the model
            control.done = true;
            console.log("Done!");
            $(playPauseButton.children()[0]).html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-stop\"></span>");
            break;
        case "model_params":
            model_params = msg["params"];
            initGUI();
            break;
        default:
            // There shouldn't be any other message
            console.log("Unexpected message.");
    }
};

/**     Turn an object into a string to send to the server, and send it. v*/
var send = function (message) {
    msg = JSON.stringify(message);
    ws.send(msg);
};

/** Reset the model, and rest the appropriate local variables. */
var reset = function ($e) {
    if ($e !== undefined)
        $e.preventDefault();

    control.tick = -1;
    control.last_sent = -1;
    control.done = false;
    control.data = [];
    control.run_number += 1;
    send({"type": "reset", "run_num": control.run_number});
    // Reset all the visualizations
    clear_graphs();
    if (!group_changed) show_group($(".list-group-item")[1]);

    if (!control.running) {
        $(playPauseButton.children()[0]).html('<span style="font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);" class="glyphicon glyphicon-play"></span>');
    } else {
        $(playPauseButton.children()[0]).html('<span style="font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);" class="glyphicon glyphicon-pause"></span>');
    }
    send({"type": "get_steps", "step": control.data.length, "fps": 10, "run_num": control.run_number});

    return false;
};

/** Send a message to the server get the next visualization state. */
var single_step = function () {
    control.tick += 1;
    let fps = parseInt(fpsControl[0].value);

    if (control.tick > control.data.length - fps * 2 && control.last_sent !== control.data.length) {
        control.last_sent = control.data.length;
        if (!control.done) send({
            "type": "get_steps",
            "step": control.data.length,
            "fps": fps,
            "run_num": control.run_number
        });
    } else {
        if (!control.done) send({
            "type": "get_steps",
            "step": control.data.length,
            "fps": fps,
            "run_num": control.run_number
        });
    }
    update_graphs();
};

/** Step the model forward. */
var step = function ($e) {
    if ($e !== undefined) $e.preventDefault();

    if (!control.running && !control.done) {
        single_step();
        update_graphs(true);
    }
    else if (!control.done) {
        run();
    }
    return false;
};

/** Step the model backward. */

var back = function ($e) {
    if ($e !== undefined) $e.preventDefault();

    if (!control.running) {
        control.tick -= 2;
        single_step();
        update_graphs(true);
    }
    return false;
};


/** Call the step function at fixed intervals, until getting an end message from the server. */
var run = function ($e) {
    // stop the page scrolling on function call
    if ($e !== undefined) $e.preventDefault();
    var anchor = $(playPauseButton.children()[0]);
    if (control.running) {
        control.running = false;
        if (player) {
            clearInterval(player);
            player = null;
        }
        anchor.html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-play\"></span>");
    }
    else if (!control.done) {
        control.running = true;
        player = setInterval(single_step, 1000 / control.fps);
        anchor.html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-pause\"></span>");
    }
    return false;
};

var updateFPS = function ($e) {
    if ($e !== undefined) $e.preventDefault();

    control.fps = Number(fpsControl.val());
    if (control.running) {
        // run twice to set interval, and clear it
        run();
        run();
    }
    return false;
};

// Initilaize buttons on top bar
playPauseButton.on('click', run);
stepButton.on('click', step);
resetButton.on('click', reset);
fpsControl.on('change', updateFPS);
backButton.on('click', back);

function update_graphs(force_draw) {
    if (control.tick < control.data.length) {
        for (var i in elements) {
            let to_render = [];
            for (let j = 0; j < control.tick; j++) {
                to_render.push(control.data[j][i])
            }

            // send all data up to current tick to be rendered, force draw when specified/every draw_delay_period
            if (to_render.length % control.draw_delay_period === 0 || force_draw === true) {
                elements[i].render(true, to_render);
            } else {
                elements[i].render(false, to_render);
            }
        }
    } else {
        control.tick -= 1;
    }
}

function clear_graphs() {
    // Reset all the visualizations
    for (var i in elements) {
        elements[i].reset();
    }
}

function show_group(group) {
    $(".list-group-item").removeClass("active");
    $(group).addClass("active");
    $(".graph_div").each(function () {
        if (group === undefined || this.dataset.for !== group.id) {
            $(this).removeClass("hidden").addClass("hidden");
        } else {
            $(this).removeClass("hidden");
        }
    });
    update_graphs(true);
    window.dispatchEvent(new Event('resize'));
    group_changed = true;
}


if (window.chrome) {
    // apply niceScroll only if chrome to avoid freezes from scroll events.
    $(function () {
        $("body").niceScroll();
    });
}


