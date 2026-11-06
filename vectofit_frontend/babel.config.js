module.exports = {
  presets: ["module:@react-native/babel-preset"],
  plugins: [
    ["./babel-plugin-vectofit-api-url", { apiUrl: process.env.VECTOFIT_API_URL }],
    "react-native-worklets/plugin",
  ],
};
