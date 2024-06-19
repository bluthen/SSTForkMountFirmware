import globals from "globals";
import pluginJs from "@eslint/js";
import pluginReactConfig from "eslint-plugin-react/configs/recommended.js";
import babelParser from '@babel/eslint-parser';


export default [
    {
        languageOptions: {
            parser: babelParser
        }
    },
    {files: ["**/*.{js,mjs,cjs,jsx}"]},
    {languageOptions: {parserOptions: {ecmaFeatures: {jsx: true}}}},
    {languageOptions: {globals: globals.browser}},
    pluginJs.configs.recommended,
    pluginReactConfig,
    {rules: {'no-unused-vars': 'off'}}
];
