import { createTheme } from '@mui/material/styles';

const defaultTheme = createTheme();

const darkTheme = createTheme({
    palette: {
        mode: 'dark'
    }
});

const redTheme = createTheme({
    palette: {
        mode: 'dark'
    }
});


export {defaultTheme, darkTheme, redTheme};