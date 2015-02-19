/** Generates a random team. **/

require('sugar');
var fs = require('fs');
var path = require('path');

global.toId = function (text) {
        if (text && text.id) text = text.id;
        else if (text && text.userid) text = text.userid;

        return string(text).toLowerCase().replace(/[^a-z0-9]+/g, '');
};
global.string = function (str) {
        if (typeof str === 'string' || typeof str === 'number') return '' + str;
        return '';
};

try {
        global.Config = require('./config/config.js');
} catch (err) {
        if (err.code !== 'MODULE_NOT_FOUND') throw err;

        // Copy it over synchronously from config-example.js since it's needed before we can start the server
        fs.writeFileSync(path.resolve(__dirname, 'config/config.js'),
                fs.readFileSync(path.resolve(__dirname, 'config/config-example.js'))
        );
        global.Config = require('./config/config.js');
}

global.Tools = require('./tools.js');

global.BattleEngine = require('./battle-engine.js');
global.Tools.random = global.BattleEngine.Battle.prototype.random;
global.Tools.nextFrame = global.BattleEngine.Battle.prototype.nextFrame;
global.Tools.init = global.BattleEngine.Battle.prototype.init;
global.Tools.init();
global.Tools.debug = function () {};
global.Tools.randomTeam = global.Tools.data.Scripts.randomTeam;
global.Tools.install(global.Tools);

console.log('[')
console.log(JSON.stringify(global.Tools.randomTeam()));
for (var i = 1; i < process.argv[2]; i++ ) {
    console.log(',');
    console.log(JSON.stringify(global.Tools.randomTeam()));
}
console.log(']');

process.exit();
