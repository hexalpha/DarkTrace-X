import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';

export default tseslint.config(
  {ignores:['.next/**','node_modules/**','next-env.d.ts']},
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {languageOptions:{globals:{process:'readonly'}},plugins:{'react-hooks':hooks},rules:{
    '@typescript-eslint/no-unused-vars':['warn',{argsIgnorePattern:'^_',varsIgnorePattern:'^_'}],
    'react-hooks/rules-of-hooks':'error',
    'react-hooks/exhaustive-deps':'warn'
  }}
);
