import React, { useState } from 'react';
import styles from '../styles/MorphologicalCalibrationScreenStyles';
import { View, Text, Pressable } from 'react-native';
import { Camera } from 'react-native-vision-camera';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';

type MorphologicalCalibrationScreenProps = NativeStackScreenProps<
    RootStackParamList,
    'MorphologicalCalibration'
>;

interface User {
    name: string;
    age: number;
    weight: number;
    height: number;
}

interface MorphologicalData {
    left_lower_limb: number;
    right_lower_limb: number;
    trunk: number;
}

interface CameraStatus {
    camera_is_active: boolean;
    person_is_detected: boolean;
    body_fully_visible: boolean;
    landmark_confidence: number;
}

interface Landmark {
    x_coordinate: number;
    y_coordinate: number;
    z_coordinate: number;
    visibility: number;
}

interface Landmarks {
    left_shoulder: Landmark;
    right_shoulder: Landmark;
    left_hip: Landmark;
    right_hip: Landmark;
    left_knee: Landmark;
    right_knee: Landmark;
    left_ankle: Landmark;
    right_ankle: Landmark;
}

{/*
interface MorphologicalAnalysis {
    lower_limb_symmetry: number;
    trunk_to_lower_limb_ratio: number;
    body_proportion_score: number;
}
*/}

type CalibrationPosition = | 'front' | 'side' | '45_degree';

export default function MorphologicalCalibrationScreen ({
    route,

}: MorphologicalCalibrationScreenProps) {
    
    const [ user, setUser ] = useState<User>({
        name: "",
        age: 0,
        weight: 0,
        height: 0,
    });

    const [ morphological_data ] = useState<MorphologicalData>({
        left_lower_limb: 0,
        right_lower_limb: 0,
        trunk: 0,
    });

    const [ camera_status ] = useState<CameraStatus> ({
        camera_is_active: false,
        person_is_detected: false,
        body_fully_visible: false,
        landmark_confidence: 0,
    });

    const [ landmark ] = useState<Landmark> ({
        x_coordinate: 0,
        y_coordinate: 0,
        z_coordinate: 0,
        visibility: 0,
    });

    const [ landmarks ] = useState<Landmarks> ({
        left_shoulder: landmark,
        right_shoulder: landmark,
        left_hip: landmark,
        right_hip: landmark,
        left_knee: landmark,
        right_knee: landmark,
        left_ankle: landmark,
        right_ankle: landmark,
    });

    {/*
    const [ morphological_analysis ] = useState<MorphologicalAnalysis> ({
        lower_limb_symmetry: 0,
        trunk_to_lower_limb_ratio: 0,
        body_proportion_score: 0,
    })
    */}

    const [ calibration_position, setCalibrationPosition ] = useState<CalibrationPosition>('front');

    return (
        <View style={styles.parentContainer}>
            <Text style={styles.headerContainer}>Morphological Calibration</Text>
            <Text>Let us customize your body type.</Text>
            <Text>Stand in the frame to extract your body landmarks.</Text>
            <Text></Text>
        </View>
    );
}

interface CameraPreviewProps {
    camera_status: CameraStatus;
}

function CameraPreview({ camera_status }: CameraPreviewProps) {
    return (
        <View style={styles.childContainer}>
            <Text>User in Frame</Text>
            <Text>{camera_status.camera_is_active ? 'Active' : 'Inactive'}</Text>
            <Text>{camera_status.person_is_detected ? 'Detected' : 'Not Detected'}</Text>
            <Text>{camera_status.body_fully_visible ? 'Fully Visible' : 'Incomplete'}</Text>
            <Text>{camera_status.landmark_confidence}</Text>
        </View>
    );
}

interface LandmarkDetectionProps {
    landmarks: Landmarks;
}

function LandmarkDetection({ landmarks }: LandmarkDetectionProps ) {
    return (
        <View style={styles.childContainer}>
            <Text>Left Shoulder X: {landmarks.left_shoulder.x_coordinate}</Text>
            <Text>Right Shoulder X: {landmarks.right_shoulder.x_coordinate}</Text>
            <Text>Left Shoulder Y: {landmarks.left_shoulder.y_coordinate}</Text>
            <Text>Right Shoulder Y: {landmarks.right_shoulder.y_coordinate}</Text>
            <Text>Left Shoulder Z: {landmarks.left_shoulder.z_coordinate}</Text>
            <Text>Right Shoulder Z: {landmarks.right_shoulder.z_coordinate}</Text>
            <Text>Left Shoulder Visibility: {landmarks.left_shoulder.visibility}</Text>
            <Text>Right Shoulder Visibility: {landmarks.right_shoulder.visibility}</Text>

            <Text>Left Hip X: {landmarks.left_hip.x_coordinate}</Text>
            <Text>Right Hip X: {landmarks.right_hip.x_coordinate}</Text>
            <Text>Left Hip Y: {landmarks.left_hip.y_coordinate}</Text>
            <Text>Right Hip Y: {landmarks.right_hip.y_coordinate}</Text>
            <Text>Left Hip Z: {landmarks.left_hip.z_coordinate}</Text>
            <Text>Right Hip Z: {landmarks.right_hip.z_coordinate}</Text>
            <Text>Left Hip Visibility: {landmarks.left_hip.visibility}</Text>
            <Text>Right Hip Visibility: {landmarks.right_hip.visibility}</Text>

            <Text>Left Knee X: {landmarks.left_knee.x_coordinate}</Text>
            <Text>Right Knee X: {landmarks.right_knee.x_coordinate}</Text>
            <Text>Left Knee Y: {landmarks.left_knee.y_coordinate}</Text>
            <Text>Right Knee Y: {landmarks.right_knee.y_coordinate}</Text>
            <Text>Left Knee Z: {landmarks.left_knee.z_coordinate}</Text>
            <Text>Right Knee Z: {landmarks.right_knee.z_coordinate}</Text>
            <Text>Left Knee Visibility: {landmarks.left_knee.visibility}</Text>
            <Text>Right Knee Visibility: {landmarks.right_knee.visibility}</Text>

            <Text>Left Ankle X: {landmarks.left_ankle.x_coordinate}</Text>
            <Text>Right Ankle X: {landmarks.right_ankle.x_coordinate}</Text>
            <Text>Left Ankle Y: {landmarks.left_ankle.y_coordinate}</Text>
            <Text>Right Ankle Y: {landmarks.right_ankle.y_coordinate}</Text>
            <Text>Left Ankle Z: {landmarks.left_ankle.z_coordinate}</Text>
            <Text>Right Ankle Z: {landmarks.right_ankle.z_coordinate}</Text>
            <Text>Left Ankle Visibility: {landmarks.left_ankle.visibility}</Text>
            <Text>Right Ankle Visibility: {landmarks.right_ankle.visibility}</Text>
        </View>
    );
}

interface CalibrationPositionProps {
    calibration_position: CalibrationPosition;
    landmark: Landmark;
}

function CalibrationPosition({ calibration_position, landmark }: CalibrationPositionProps) {
    return (
        <View>
            <Text>Current Position: {calibration_position}</Text>
        </View>
    );
}

{/*
interface MorphologicalAnalysisProps {
    morphological_analysis: MorphologicalAnalysis;
}

function MorphologicalAnalysis({ morphological_analysis }: MorphologicalAnalysisProps) {
    return (
        <View style={styles.childContainer}>
            <Text>Your Body Measurements</Text>
            <Text>Lower Limb Symmetry: {morphological_analysis.lower_limb_symmetry}</Text>
            <Text>Trunk-Lower Limb Ratio: {morphological_analysis.trunk_to_lower_limb_ratio}</Text>
            <Text>Body Proportion Score: {morphological_analysis.body_proportion_score}</Text>
        </View>
    );
}
*/}