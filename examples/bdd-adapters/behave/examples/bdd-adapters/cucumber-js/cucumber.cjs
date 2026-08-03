// cucumber-js reads the feature `compass bdd extract` wrote. The extracted
// file is derived - regenerate it whenever the spec changes; never edit it.
module.exports = {
  default: {
    paths: ['features/*.feature'],
    import: ['features/step_definitions/*.mjs'],
  },
};
