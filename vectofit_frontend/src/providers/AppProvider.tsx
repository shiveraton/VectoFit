import React, { ReactNode } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { QueryClient, QueryClientProvider, queryOptions } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            refetchOnWindowFocus: false,
            staleTime: 1000 * 60 * 5,
        },
    },
});

interface AppProviderProps {
    children: ReactNode;
}

export const AppProvider = ({children}: AppProviderProps) => {
    return (
        <QueryClientProvider client={queryClient}>
            <SafeAreaProvider>
                {children}
            </SafeAreaProvider>
        </QueryClientProvider>
    );
};

export default AppProvider;