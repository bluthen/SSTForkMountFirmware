/* global require */
const CopyWebpackPlugin = require('copy-webpack-plugin');
const UglifyJSPlugin = require('uglifyjs-webpack-plugin');
const webpack = require('webpack');


module.exports = env => {
    const isProd = env ? env.production : false;
    console.log(isProd);

    function setDevTool() {
        //return 'eval-source-map';
        if (isProd) {
            return 'source-map';
        } else {
            return 'eval-source-map';
        }
    }

    const config = {
        entry: __dirname + "/src/app/index.js",
        output: {
            path: __dirname + '/dist',
            filename: 'app.js',
            publicPath: '/',
            pathinfo: true
        },
        devtool: setDevTool(),
        module: {
            rules: [
                {
                    test: /\.js$/,
                    exclude: [
                        /node_modules/
                    ],
                    use: {
                        loader: 'babel-loader',
                        options: {
                            presets: ['env']
                        }
                    }
                },
                {
                    test: /\.html/,
                    loader: 'raw-loader'
                },
                {
                    test: /\.(sass|scss)$/,
                    use: [{
                        loader: "style-loader" // creates style nodes from JS strings
                    }, {
                        loader: "css-loader" // translates CSS into CommonJS
                    }, {
                        loader: "sass-loader" // compiles Sass to CSS
                    }]
                }
            ]
        },
        plugins: [],
        devServer: {
            contentBase: './src/public',
            port: 7700,
        },
        optimization: {
            minimizer: [new UglifyJSPlugin({sourceMap: true})]
        }
    };

    if (isProd) {
        config.plugins.push(
            new CopyWebpackPlugin([{
                from: __dirname + '/src/public/'
            }])
        );
    }

    return config;

};
