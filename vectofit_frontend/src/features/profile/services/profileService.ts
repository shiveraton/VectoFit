import apiClient from '../../../api/client';

export const getProfiles = async () => {
    const response = await apiClient.get('/accounts/profile/');
    return response.data;
};