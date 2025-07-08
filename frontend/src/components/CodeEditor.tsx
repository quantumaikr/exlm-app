import React from 'react';
import { Box } from '@mui/material';
import Editor from '@monaco-editor/react';
import { useTheme } from '@mui/material/styles';

interface CodeEditorProps {
  value: string;
  onChange: (value: string | undefined) => void;
  language?: string;
  height?: string;
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'python',
  height = '400px',
  readOnly = false,
}) => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={onChange}
        theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'light'}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          readOnly,
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          automaticLayout: true,
        }}
      />
    </Box>
  );
};

export default CodeEditor;