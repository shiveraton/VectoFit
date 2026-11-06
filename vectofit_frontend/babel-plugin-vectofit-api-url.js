module.exports = function inlineVectoFitApiUrl({ types: t }) {
  return {
    visitor: {
      Identifier(path, state) {
        if (path.node.name !== "__VECTOFIT_API_URL__" || !path.isReferencedIdentifier()) {
          return;
        }

        const apiUrl = state.opts.apiUrl;
        if (typeof apiUrl !== "string" || !apiUrl.trim()) {
          throw path.buildCodeFrameError(
            "Set VECTOFIT_API_URL before starting Metro or building the app.",
          );
        }

        path.replaceWith(t.stringLiteral(apiUrl.trim().replace(/\/+$/, "")));
      },
    },
  };
};
