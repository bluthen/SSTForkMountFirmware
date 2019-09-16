var path = require('path');
var webpack = require('webpack');

module.exports = {
    devtool: 'eval',
    mode: 'development',
	devServer: {
		proxy: {
			'/api': 'http://localhost:5000',
			'/advanced_slew_limits': 'http://localhost:5000'
		}
	},
    entry: [
        './src/index'
    ],
    output: {
        path: path.join(__dirname, 'dist'),
        filename: 'bundle.js',
        publicPath: '/static/'
    },
    plugins: [
        new webpack.HotModuleReplacementPlugin()
    ],
    resolve: {
        extensions: ['.js', '.jsx']
    },
    module: {
        rules: [{
            test: /\.jsx?$/,
            use: {
                loader: 'babel-loader',
                options: {
                    presets: [
                        "@babel/preset-react",
                        "@babel/preset-env"
                    ],
                    plugins: [
                        "@babel/plugin-transform-runtime",
                        ["@babel/plugin-proposal-decorators", {"legacy": true}],
                        "@babel/plugin-proposal-class-properties",
                        "@babel/plugin-proposal-optional-chaining",
                        ["@babel/plugin-proposal-pipeline-operator", {"proposal": "minimal"}]
                    ]
                },
            },
            include: path.join(__dirname, 'src')
        },
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader']
            },
            {
                test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
                use: [
                    {
                        loader: 'file-loader',
                        options: {
                            name: '[name].[ext]',
                            outputPath: 'fonts/'
                        }
                    }
                ]
            }
        ]
    }
};
