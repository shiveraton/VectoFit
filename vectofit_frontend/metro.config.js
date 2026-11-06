// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require("expo/metro-config");

const expoEnv = require("@expo/env");
expoEnv.setNodeEnv(process.env.NODE_ENV === "production" ? "production" : "development");
expoEnv.loadProjectEnv(__dirname);

/** @type {import("expo/metro-config").MetroConfig} */
const config = getDefaultConfig(__dirname);

module.exports = config;
