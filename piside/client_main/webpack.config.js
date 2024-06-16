const path = require('path');
const webpack = require('webpack');

module.exports = {
    devtool: 'source-map',
    mode: 'development',
    devServer: {
        proxy: [
            {context: ['/api'], target: 'http://localhost:5000'},
            {context: ['/advanced_slew_limits'], target: 'http://localhost:5000'}
        ],
        static: {
            directory: __dirname,
            serveIndex: true
        },
        client: {
            overlay: false
        },
        compress: true,
        open: false,
        hot: true
    },
    entry: [
        './src/index'
    ],
    output: {
        path: path.join(__dirname, 'dist'),
        filename: 'bundle.js',
        publicPath: '/static/'
    },
    resolve: {
        extensions: ['.js', '.jsx']
    },
    module: {
        rules: [
            {
                test: /\.jsx?$/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: [
                            "@babel/preset-react",
                            "@babel/preset-env"
                        ],
                        plugins: [
                            ["@babel/plugin-proposal-decorators", {"version": '2023-05'}]
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
