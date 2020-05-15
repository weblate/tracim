const path = require('path')
const isProduction = process.env.NODE_ENV === 'production'

module.exports = {
  mode: isProduction ? 'production' : 'development',
  entry: {
    main: './dist/index.js'
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: isProduction ? 'vendors.js' : 'vendors.dev.js',
    pathinfo: !isProduction,
    library: 'tracim_frontend_vendors',
    libraryTarget: 'var'
  },
  module: {
    rules: [{
      test: /\.jsx?$/,
      enforce: 'pre',
      use: 'standard-loader',
      exclude: [/node_modules/]
    }, {
      test: [/\.js$/, /\.jsx$/],
      exclude: [/node_modules/],
      loader: 'babel-loader',
      options: {
        presets: [
          '@babel/preset-env',
          '@babel/preset-react'
        ],
        plugins: [
          '@babel/plugin-proposal-object-rest-spread',
          '@babel/plugin-proposal-class-properties',
          '@babel/plugin-transform-object-assign'
        ]
      }
    }]
  },
  devtool: isProduction ? false : 'cheap-module-source-map',
  performance: {
    hints: false
  }
}
