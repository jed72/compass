// cucumber-js reads the feature `compass bdd extract` wrote. That file is
// derived - regenerate it whenever the spec changes; never edit it.
module.exports = {
  default: {
    paths: ['features/*.feature'],
    require: ['features/step_definitions/*.js'],
  },
};
