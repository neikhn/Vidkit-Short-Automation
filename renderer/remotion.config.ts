import {Config} from '@remotion/cli/config';
import path from 'node:path';

Config.overrideWebpackConfig((config) => ({
  ...config,
  resolve: {
    ...config.resolve,
    modules: [path.resolve(__dirname, 'node_modules'), ...(config.resolve?.modules ?? ['node_modules'])],
  },
}));

const studioOutput = process.env.VIDKIT_STUDIO_OUTPUT;

if (studioOutput) {
  Config.setOutputLocation(studioOutput);
}
